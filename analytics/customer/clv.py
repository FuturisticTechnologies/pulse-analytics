"""Customer lifetime value.

Three estimates, deliberately, because a single CLV number always hides an
assumption:

1. **Historic CLV** - what the customer has actually paid us. Certain, and
   useless for deciding what to spend acquiring the *next* one.
2. **Predicted CLV** - a discounted expected-value model:

       CLV = ARPU_month x gross_margin x expected_remaining_months, discounted

   where expected remaining months comes from the observed monthly retention
   rate (a geometric survival assumption: r/(1-r)). Simple, transparent, and
   the coefficients are all things a finance team already tracks.
3. **Cohort-curve CLV** - extrapolating the cumulative-LTV curve of mature
   cohorts onto young ones. It needs no behavioural assumption at all, which
   makes it the sanity check on (2).

The three will not agree exactly. Where they diverge sharply is a finding, not
a bug - usually it means retention has genuinely changed between cohorts.

    python -m analytics.customer.clv
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from analytics.common import datasets
from pulse.logging_utils import banner, get_logger

log = get_logger("analytics.clv")

MONTHLY_DISCOUNT_RATE = 0.01     # ~12.7% annual cost of capital
MAX_HORIZON_MONTHS = 36          # do not forecast value beyond three years


def monthly_retention_rate() -> float:
    """Average month-over-month retention across the observed history.

    Taken from gold.mart_churn_monthly so the number the CLV model uses is the
    same number the retention dashboard shows.
    """
    from pulse.db import get_database

    frame = get_database().query(
        "SELECT retention_rate_pct FROM gold.mart_churn_monthly "
        "WHERE retention_rate_pct IS NOT NULL"
    )
    if frame.empty:
        return 0.5
    return float(np.clip(frame["retention_rate_pct"].mean() / 100.0, 0.01, 0.99))


def expected_remaining_months(retention: float) -> float:
    """Geometric survival: E[lifetime] = r / (1 - r) months from now."""
    retention = float(np.clip(retention, 0.01, 0.98))
    return min(retention / (1 - retention), MAX_HORIZON_MONTHS)


def discounted_value(monthly_value: float, months: float,
                     rate: float = MONTHLY_DISCOUNT_RATE) -> float:
    """Present value of an annuity of ``monthly_value`` over ``months``."""
    if months <= 0:
        return 0.0
    periods = np.arange(1, int(round(months)) + 1)
    return float((monthly_value / (1 + rate) ** periods).sum())


def compute_clv(frame: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per-customer historic and predicted CLV."""
    frame = datasets.buyers() if frame is None else frame.copy()
    retention = monthly_retention_rate()
    horizon = expected_remaining_months(retention)

    active_months = (frame["tenure_days"].clip(lower=30) / 30.4375)
    frame["arpu_monthly"] = (frame["lifetime_revenue"] / active_months).round(2)
    frame["margin_rate"] = (
        frame["lifetime_profit"] / frame["lifetime_revenue"].replace(0, np.nan)
    ).fillna(0).clip(0, 1)

    frame["historic_clv"] = frame["lifetime_profit"].round(2)
    frame["expected_months_remaining"] = round(horizon, 1)
    frame["predicted_clv"] = [
        round(discounted_value(arpu * margin, horizon), 2)
        for arpu, margin in zip(frame["arpu_monthly"], frame["margin_rate"])
    ]
    # A churned customer has no remaining value to discount.
    frame.loc[frame["is_churned"], "predicted_clv"] = 0.0
    frame["total_clv"] = (frame["historic_clv"] + frame["predicted_clv"]).round(2)

    frame["clv_decile"] = pd.qcut(
        frame["total_clv"].rank(method="first"), 10,
        labels=[f"D{i}" for i in range(1, 11)],
    )
    log.info("monthly retention %.1f%% -> expected remaining life %.1f months",
             retention * 100, horizon)
    return frame.sort_values("total_clv", ascending=False)


def clv_by_segment(scored: pd.DataFrame, by: str = "acquisition_channel") -> pd.DataFrame:
    return (
        scored.groupby(by)
        .agg(customers=("customer_id", "count"),
             avg_historic_clv=("historic_clv", "mean"),
             avg_predicted_clv=("predicted_clv", "mean"),
             avg_total_clv=("total_clv", "mean"),
             total_clv=("total_clv", "sum"))
        .round(2)
        .sort_values("avg_total_clv", ascending=False)
        .reset_index()
    )


def ltv_to_cac(scored: pd.DataFrame) -> pd.DataFrame:
    """LTV:CAC per acquisition channel - the number that sets the budget.

    Rule of thumb: below 1.0 the channel destroys value; 3.0 or better is
    healthy. Channels with no measured spend are shown with a null ratio rather
    than an infinite one.
    """
    from pulse.db import get_database

    acquisition = get_database().query("""
        SELECT channel, spend, new_customers, cac
        FROM gold.mart_channel_performance
    """)
    by_channel = clv_by_segment(scored, "acquisition_channel")
    merged = by_channel.merge(
        acquisition, left_on="acquisition_channel", right_on="channel", how="left"
    )
    merged["ltv_cac_ratio"] = (merged["avg_total_clv"] / merged["cac"]).round(2)
    merged["verdict"] = np.select(
        [merged["ltv_cac_ratio"].isna(),
         merged["ltv_cac_ratio"] < 1,
         merged["ltv_cac_ratio"] < 3],
        ["No measured spend", "Destroying value", "Marginal"],
        default="Healthy",
    )
    return merged[["acquisition_channel", "customers", "avg_total_clv", "cac",
                   "ltv_cac_ratio", "verdict"]]


def cohort_curve_clv() -> pd.DataFrame:
    """Extrapolate mature cohorts' cumulative-LTV curve onto younger ones.

    Uses the average cumulative LTV at each month-since-acquisition across all
    cohorts old enough to have reached it, then projects each cohort forward
    along that shape. No behavioural assumption - just "new cohorts behave like
    old ones", which is testable and visibly wrong when it is wrong.
    """
    cohorts = datasets.cohorts()
    if cohorts.empty:
        return cohorts

    # MEDIAN, not mean: one cohort containing a whale would otherwise define
    # the shape of the curve for every other cohort. And the index is forced
    # non-decreasing with cummax - cumulative LTV cannot fall, so a dip is
    # sampling noise from thin cohorts, not a real behaviour.
    curve = (
        cohorts.groupby("months_since")["cumulative_ltv"]
        .median().round(2).rename("avg_cumulative_ltv").reset_index()
    )
    curve["avg_cumulative_ltv"] = curve["avg_cumulative_ltv"].cummax()
    curve["ltv_index"] = (curve["avg_cumulative_ltv"] /
                          max(curve["avg_cumulative_ltv"].iloc[0], 0.01)).round(3)

    latest = (
        cohorts.sort_values("months_since")
        .groupby("cohort_month")
        .agg(cohort_customers=("cohort_customers", "max"),
             months_observed=("months_since", "max"),
             ltv_to_date=("cumulative_ltv", "last"))
        .reset_index()
    )
    index_lookup = curve.set_index("months_since")["ltv_index"]
    horizon = int(curve["months_since"].max())

    latest["ltv_index_now"] = latest["months_observed"].map(index_lookup).fillna(1.0)
    latest["projected_ltv_month_12"] = (
        latest["ltv_to_date"] * index_lookup.get(min(12, horizon), 1.0)
        / latest["ltv_index_now"]
    ).round(2)
    latest["projected_cohort_value"] = (
        latest["projected_ltv_month_12"] * latest["cohort_customers"]
    ).round(2)
    return latest.sort_values("cohort_month")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Customer lifetime value")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args(argv)

    print(banner("PulseAnalytics - customer lifetime value"))
    scored = compute_clv()

    print("\nCLV by acquisition channel")
    print(clv_by_segment(scored).to_string(index=False))

    print("\nLTV : CAC")
    print(ltv_to_cac(scored).to_string(index=False))

    print("\nCLV by loyalty tier")
    print(clv_by_segment(scored, "loyalty_tier").to_string(index=False))

    print("\nCohort curve projection")
    print(cohort_curve_clv().tail(12).to_string(index=False))

    print(f"\nTop {args.top} customers by total CLV")
    print(scored[["customer_id", "full_name", "orders", "lifetime_revenue",
                  "historic_clv", "predicted_clv", "total_clv"]]
          .head(args.top).to_string(index=False))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
