"""Behavioural customer segmentation.

Two segmentations, and they answer different questions:

* **RFM** (in SQL, ``gold.mart_rfm_segments``) is rule-based, stable and
  instantly explainable. It is what marketing briefs against.
* **k-means** (here) is data-driven and finds structure the RFM grid cannot -
  for example a group with high frequency and low basket value, which RFM
  scatters across three cells.

Running both is the honest answer: k-means alone produces clusters nobody can
name, and RFM alone hides real structure. This module fits k-means, then
*characterises* each cluster against the business features so the output is a
named, actionable segment rather than "cluster 3".

    python -m analytics.customer.segmentation --k 5
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from analytics.common import datasets
from analytics.common.modelling import (
    choose_k,
    kmeans,
    log1p_positive,
    silhouette_score,
    standardise,
)
from pulse.logging_utils import banner, get_logger

log = get_logger("analytics.segmentation")

# Features chosen so a cluster is describable in one sentence to a marketer.
FEATURES = [
    "recency_days",       # how long since they bought
    "orders",             # how often
    "lifetime_revenue",   # how much
    "avg_order_value",    # basket size
    "tenure_days",        # how long we have known them
]


def build_feature_matrix(frame: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    """Log-transform the skewed money/count columns, then standardise."""
    features = pd.DataFrame(index=frame.index)
    features["recency_days"] = frame["recency_days"].fillna(frame["recency_days"].max())
    features["orders"] = log1p_positive(frame["orders"])
    features["lifetime_revenue"] = log1p_positive(frame["lifetime_revenue"])
    features["avg_order_value"] = log1p_positive(frame["avg_order_value"])
    features["tenure_days"] = frame["tenure_days"].fillna(0)

    scaled, _mean, _std = standardise(features.to_numpy(dtype=float))
    return scaled, features


def name_cluster(profile: pd.Series, medians: pd.Series) -> str:
    """Turn a centroid into a label a human would use.

    Compared against the *population median* rather than fixed thresholds, so
    the names stay meaningful as the business grows.
    """
    recent = profile["recency_days"] <= medians["recency_days"]
    frequent = profile["orders"] >= medians["orders"]
    valuable = profile["lifetime_revenue"] >= medians["lifetime_revenue"]
    big_basket = profile["avg_order_value"] >= medians["avg_order_value"]
    tenured = profile["tenure_days"] >= medians["tenure_days"]

    if recent and frequent and valuable:
        return "Core Loyalists"
    if recent and big_basket and not frequent:
        return "High-Value Occasionals"
    if recent and not valuable and not tenured:
        return "Recent Starters"
    if not recent and valuable:
        return "Lapsing High Value"
    if not recent and not valuable:
        return "Dormant Low Value"
    if frequent and not big_basket:
        return "Frequent Small Baskets"
    return "Steady Middle"


def segment_customers(k: int = 5, seed: int = 42,
                      frame: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    """Fit k-means and return the labelled customers plus a cluster profile."""
    frame = datasets.buyers() if frame is None else frame.copy()
    if frame.empty:
        raise ValueError("no purchasing customers to segment")

    matrix, features = build_feature_matrix(frame)
    labels, centroids, inertia = kmeans(matrix, k, seed=seed)
    score = silhouette_score(matrix, labels, seed=seed)
    log.info("k=%d inertia=%.1f silhouette=%.3f", k, inertia, score)

    labelled = frame.copy()
    labelled["cluster"] = labels

    # Profile every cluster on the ORIGINAL scale - a centroid in z-space is
    # meaningless to the person who has to act on it.
    profile = labelled.groupby("cluster").agg(
        customers=("customer_id", "count"),
        avg_recency_days=("recency_days", "mean"),
        avg_orders=("orders", "mean"),
        avg_lifetime_revenue=("lifetime_revenue", "mean"),
        avg_order_value=("avg_order_value", "mean"),
        avg_tenure_days=("tenure_days", "mean"),
        total_revenue=("lifetime_revenue", "sum"),
        repeat_rate_pct=("is_repeat_buyer", "mean"),
        churned_pct=("is_churned", "mean"),
    ).round(2)
    profile["repeat_rate_pct"] = (profile["repeat_rate_pct"] * 100).round(1)
    profile["churned_pct"] = (profile["churned_pct"] * 100).round(1)
    profile["customer_share_pct"] = (
        profile["customers"] / profile["customers"].sum() * 100).round(1)
    profile["revenue_share_pct"] = (
        profile["total_revenue"] / profile["total_revenue"].sum() * 100).round(1)

    medians = pd.Series({
        "recency_days": labelled["recency_days"].median(),
        "orders": labelled["orders"].median(),
        "lifetime_revenue": labelled["lifetime_revenue"].median(),
        "avg_order_value": labelled["avg_order_value"].median(),
        "tenure_days": labelled["tenure_days"].median(),
    })
    naming_input = profile.rename(columns={
        "avg_recency_days": "recency_days",
        "avg_orders": "orders",
        "avg_lifetime_revenue": "lifetime_revenue",
        "avg_order_value": "avg_order_value",
        "avg_tenure_days": "tenure_days",
    })
    names = {
        cluster: name_cluster(naming_input.loc[cluster], medians)
        for cluster in profile.index
    }
    # Two clusters can legitimately earn the same description; disambiguate so
    # the label stays a usable key.
    seen: dict[str, int] = {}
    for cluster, name in list(names.items()):
        seen[name] = seen.get(name, 0) + 1
        if seen[name] > 1:
            names[cluster] = f"{name} {seen[name]}"

    profile["segment_name"] = [names[c] for c in profile.index]
    labelled["segment_name"] = labelled["cluster"].map(names)

    return {
        "customers": labelled,
        "profile": profile.reset_index(),
        "diagnostics": pd.DataFrame([{
            "k": k, "inertia": round(inertia, 2), "silhouette": score,
            "customers": len(labelled), "features": ", ".join(FEATURES),
        }]),
    }


def compare_with_rfm(labelled: pd.DataFrame) -> pd.DataFrame:
    """Cross-tab of k-means segments against the SQL RFM segments.

    Where the two agree, confidence is high. Where they disagree is where the
    interesting customers are, and it is the first thing worth reviewing.
    """
    rfm = datasets.rfm()[["customer_id", "rfm_segment"]]
    merged = labelled.merge(rfm, on="customer_id", how="left")
    return (
        pd.crosstab(merged["segment_name"], merged["rfm_segment"].fillna("Unscored"))
        .reset_index()
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cluster customers by behaviour")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--choose-k", action="store_true",
                        help="report inertia and silhouette for k=2..7 and exit")
    args = parser.parse_args(argv)

    print(banner("PulseAnalytics - customer segmentation"))
    frame = datasets.buyers()

    if args.choose_k:
        matrix, _ = build_feature_matrix(frame)
        print(choose_k(matrix, seed=args.seed).to_string(index=False))
        print("\nPick the k where silhouette peaks AND the smallest cluster is "
              "still large enough to run a campaign against.\n")
        return 0

    result = segment_customers(k=args.k, seed=args.seed, frame=frame)
    print("\nCluster profile")
    print(result["profile"].to_string(index=False))
    print("\nAgainst the RFM segmentation")
    print(compare_with_rfm(result["customers"]).to_string(index=False))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
