"""Churn propensity scoring.

Churn is *defined* in SQL (no order for CHURN_WINDOW_DAYS, see
docs/kpi-definitions.md). This module answers the forward-looking question the
definition cannot: **which currently-active customers are about to churn**.

Method: logistic regression on behavioural features, fitted on features computed at
the analysis date and labelled by current churn state. That framing matters more than the choice of model:

* Training on features computed *today* against a label of *today* leaks the
  future and produces a model with a beautiful AUC and no predictive value -
  the single most common mistake in a churn project.
* By rewinding the features, every input was genuinely knowable at prediction
  time.

A linear model is used deliberately. Its coefficients are the deliverable
alongside the scores: retention teams act on *why* a customer is at risk, and
"recency is the dominant driver, support contacts add materially" is something
they can build a campaign from.

    python -m analytics.customer.churn
"""
from __future__ import annotations

import argparse
from datetime import timedelta

import numpy as np
import pandas as pd

from analytics.common import datasets
from analytics.common.modelling import (
    fit_logistic,
    predict_logistic,
    roc_auc,
    standardise,
    train_test_split,
)
from pulse.config import CHURN_WINDOW_DAYS
from pulse.db import get_database
from pulse.logging_utils import banner, get_logger

log = get_logger("analytics.churn")

FEATURE_NAMES = [
    "recency_days",
    "orders",
    "avg_order_value",
    "tenure_days",
    "order_frequency_per_month",
    "avg_days_between_orders",
    "discount_share",
    "return_rate",
    "support_contacts",
]


def build_training_snapshot(observation_days: int = CHURN_WINDOW_DAYS) -> pd.DataFrame:
    """Rewind the clock and label what happened next.

    Features are computed from orders placed on or before ``cutoff``; the label
    is whether the customer ordered again in the ``observation_days`` after it.
    """
    db = get_database()
    as_of = datasets.analysis_date(db)
    cutoff = as_of - timedelta(days=observation_days)

    orders = datasets.orders(db)
    orders = orders[orders["is_revenue"]].copy()
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    cutoff_ts = pd.Timestamp(cutoff)

    history = orders[orders["order_date"] <= cutoff_ts]
    future = orders[orders["order_date"] > cutoff_ts]
    if history.empty:
        raise ValueError("no order history before the cutoff - dataset is too short")

    grouped = history.groupby("customer_id")
    snapshot = pd.DataFrame({
        "orders": grouped.size(),
        "lifetime_revenue": grouped["net_amount"].sum(),
        "avg_order_value": grouped["net_amount"].mean(),
        "discounts": grouped["discount_amount"].sum(),
        "first_order_date": grouped["order_date"].min(),
        "last_order_date": grouped["order_date"].max(),
        "avg_days_between_orders": grouped["days_since_prev_order"].mean(),
    }).reset_index()

    snapshot["recency_days"] = (cutoff_ts - snapshot["last_order_date"]).dt.days
    snapshot["tenure_days"] = (cutoff_ts - snapshot["first_order_date"]).dt.days
    snapshot["order_frequency_per_month"] = (
        snapshot["orders"] / (snapshot["tenure_days"].clip(lower=30) / 30.0)
    )
    snapshot["discount_share"] = (
        snapshot["discounts"] / snapshot["lifetime_revenue"].replace(0, np.nan)
    ).fillna(0)
    snapshot["avg_days_between_orders"] = snapshot["avg_days_between_orders"].fillna(
        snapshot["tenure_days"].clip(lower=1)
    )

    # Behavioural signals from outside the order stream.
    customers = datasets.customers(db)[
        ["customer_id", "support_contacts", "orders_returned", "loyalty_tier",
         "acquisition_channel", "region_key"]
    ]
    snapshot = snapshot.merge(customers, on="customer_id", how="left")
    snapshot["support_contacts"] = snapshot["support_contacts"].fillna(0)
    snapshot["return_rate"] = (
        snapshot["orders_returned"].fillna(0) / snapshot["orders"].clip(lower=1)
    )

    returned = set(future["customer_id"].unique())
    snapshot["churned"] = (~snapshot["customer_id"].isin(returned)).astype(int)
    snapshot["cutoff_date"] = cutoff
    log.info("training snapshot: %d customers as of %s, churn rate %.1f%%",
             len(snapshot), cutoff, snapshot["churned"].mean() * 100)
    return snapshot


def fit_churn_model(snapshot: pd.DataFrame | None = None, seed: int = 42) -> dict:
    """Fit, evaluate on a held-out split, and return the model bundle."""
    snapshot = build_training_snapshot() if snapshot is None else snapshot
    if snapshot["churned"].nunique() < 2:
        raise ValueError("every customer has the same outcome - cannot fit a model")

    train, test = train_test_split(snapshot, test_fraction=0.25, seed=seed)

    train_features = train[FEATURE_NAMES].to_numpy(dtype=float)
    scaled_train, mean, std = standardise(train_features)
    weights = fit_logistic(scaled_train, train["churned"].to_numpy(dtype=float))

    scaled_test = (test[FEATURE_NAMES].to_numpy(dtype=float) - mean) / std
    train_auc = roc_auc(train["churned"].to_numpy(), predict_logistic(weights, scaled_train))
    test_auc = roc_auc(test["churned"].to_numpy(), predict_logistic(weights, scaled_test))

    coefficients = pd.DataFrame({
        "feature": FEATURE_NAMES,
        "coefficient": np.round(weights[1:], 4),
    })
    # Standardised inputs, so |coefficient| IS the comparable effect size.
    coefficients["abs_effect"] = coefficients["coefficient"].abs()
    coefficients["direction"] = np.where(
        coefficients["coefficient"] > 0, "increases churn risk", "reduces churn risk"
    )
    coefficients = coefficients.sort_values("abs_effect", ascending=False)

    log.info("churn model AUC: train %.3f / holdout %.3f", train_auc, test_auc)
    return {
        "weights": weights, "mean": mean, "std": std,
        "coefficients": coefficients,
        "metrics": pd.DataFrame([{
            "train_rows": len(train), "test_rows": len(test),
            "train_auc": train_auc, "holdout_auc": test_auc,
            "base_churn_rate_pct": round(float(snapshot["churned"].mean() * 100), 2),
            "cutoff_date": snapshot["cutoff_date"].iloc[0],
            "observation_window_days": CHURN_WINDOW_DAYS,
        }]),
    }


def score_current_customers(model: dict | None = None) -> pd.DataFrame:
    """Apply the model to every customer active today.

    Already-churned customers are excluded: they are a win-back problem, not a
    retention problem, and mixing them in would flood the risk list with people
    it is already too late to save.
    """
    model = fit_churn_model() if model is None else model
    customers = datasets.buyers()
    live = customers[~customers["is_churned"]].copy()
    if live.empty:
        return live

    live["order_frequency_per_month"] = (
        live["orders"] / (live["tenure_days"].clip(lower=30) / 30.0)
    )
    live["discount_share"] = (
        live["lifetime_discounts"] / live["lifetime_revenue"].replace(0, np.nan)
    ).fillna(0)
    live["return_rate"] = live["orders_returned"] / live["orders"].clip(lower=1)
    live["avg_days_between_orders"] = live["avg_days_between_orders"].fillna(
        live["tenure_days"].clip(lower=1)
    )

    features = live[FEATURE_NAMES].to_numpy(dtype=float)
    scaled = (features - model["mean"]) / model["std"]
    live["churn_probability"] = np.round(predict_logistic(model["weights"], scaled), 4)

    live["risk_band"] = pd.cut(
        live["churn_probability"],
        bins=[-0.01, 0.25, 0.50, 0.75, 1.01],
        labels=["Low", "Medium", "High", "Critical"],
    )
    # What the customer is worth x how likely we are to lose them: the number
    # that should actually order the retention team's call list.
    live["revenue_at_risk"] = (
        live["projected_annual_value"] * live["churn_probability"]
    ).round(2)
    return live.sort_values("revenue_at_risk", ascending=False)


def risk_summary(scored: pd.DataFrame) -> pd.DataFrame:
    return (
        scored.groupby("risk_band", observed=False)
        .agg(customers=("customer_id", "count"),
             avg_probability=("churn_probability", "mean"),
             lifetime_revenue=("lifetime_revenue", "sum"),
             revenue_at_risk=("revenue_at_risk", "sum"))
        .round(2)
        .reset_index()
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score churn risk")
    parser.add_argument("--top", type=int, default=15, help="rows of the risk list to print")
    args = parser.parse_args(argv)

    print(banner("PulseAnalytics - churn propensity"))
    model = fit_churn_model()
    print("\nModel quality")
    print(model["metrics"].to_string(index=False))
    print("\nWhat drives churn (standardised coefficients)")
    print(model["coefficients"].to_string(index=False))

    scored = score_current_customers(model)
    print("\nRisk bands")
    print(risk_summary(scored).to_string(index=False))
    print(f"\nTop {args.top} customers by revenue at risk")
    print(scored[["customer_id", "full_name", "loyalty_tier", "recency_days", "orders",
                  "lifetime_revenue", "churn_probability", "risk_band", "revenue_at_risk"]]
          .head(args.top).to_string(index=False))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
