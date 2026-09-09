"""Market-basket / product-affinity analysis.

Finds pairs of products (and categories) bought together more often than chance
would predict. The output drives cross-sell placement, bundle pricing and the
"customers also bought" module.

Three measures, and all three are needed:

    support(A,B)     how often the pair occurs at all      - is it worth acting on
    confidence(A->B) P(B | A)                              - how strong the pull is
    lift(A,B)        confidence / P(B)                     - is it real or just popularity

Lift is the one that matters and the one usually omitted. A pair of best-sellers
will show high support and high confidence purely because both are popular; only
lift > 1 says the association is genuine. This implementation reports all three
and sorts on lift, with a minimum support floor so the top of the list is not
filled with coincidences that happened twice.

    python -m analytics.sales.basket --min-support 0.002
"""
from __future__ import annotations

import argparse
from itertools import combinations

import pandas as pd

from analytics.common import datasets
from pulse.logging_utils import banner, get_logger

log = get_logger("analytics.basket")


def build_baskets(lines: pd.DataFrame | None = None,
                  level: str = "product_name") -> pd.Series:
    """One row per order: the set of distinct items in it.

    Multi-item orders only - a single-item order carries no co-occurrence
    information and would deflate every support figure if counted.
    """
    lines = datasets.sales_lines() if lines is None else lines
    baskets = lines.groupby("order_id")[level].apply(lambda s: frozenset(s.unique()))
    return baskets[baskets.map(len) >= 2]


def affinity_pairs(baskets: pd.Series, min_support: float = 0.002,
                   min_pair_count: int = 3) -> pd.DataFrame:
    """Compute support, confidence and lift for every co-occurring pair."""
    total_baskets = len(baskets)
    if total_baskets == 0:
        return pd.DataFrame(columns=[
            "item_a", "item_b", "pair_count", "support", "confidence_a_to_b",
            "confidence_b_to_a", "lift",
        ])

    item_counts: dict[str, int] = {}
    pair_counts: dict[tuple[str, str], int] = {}
    for basket in baskets:
        items = sorted(basket)
        for item in items:
            item_counts[item] = item_counts.get(item, 0) + 1
        for pair in combinations(items, 2):
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

    rows = []
    for (item_a, item_b), count in pair_counts.items():
        if count < min_pair_count:
            continue
        support = count / total_baskets
        if support < min_support:
            continue
        support_a = item_counts[item_a] / total_baskets
        support_b = item_counts[item_b] / total_baskets
        confidence_ab = count / item_counts[item_a]
        confidence_ba = count / item_counts[item_b]
        rows.append({
            "item_a": item_a,
            "item_b": item_b,
            "pair_count": count,
            "support": round(support, 5),
            "confidence_a_to_b": round(confidence_ab, 4),
            "confidence_b_to_a": round(confidence_ba, 4),
            "lift": round(confidence_ab / support_b, 3) if support_b else 0.0,
        })

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["association"] = pd.cut(
        frame["lift"], bins=[-0.01, 0.9, 1.1, 2.0, 1e9],
        labels=["Substitutes", "Independent", "Related", "Strongly related"],
    )
    return frame.sort_values(["lift", "pair_count"], ascending=False).reset_index(drop=True)


def category_affinity(lines: pd.DataFrame | None = None) -> pd.DataFrame:
    """The same analysis at category level.

    Far more stable than product level on a catalogue of any size - most product
    pairs are too rare to trust, whereas category pairs have enough volume to
    plan a store layout or a homepage around.
    """
    baskets = build_baskets(lines, level="category")
    return affinity_pairs(baskets, min_support=0.001, min_pair_count=2)


def cross_sell_recommendations(pairs: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
    """For each anchor item, the best partners to recommend alongside it.

    Both directions of every pair are considered, because "buyers of A also buy
    B" and "buyers of B also buy A" are different recommendations with different
    strengths.
    """
    if pairs.empty:
        return pairs

    forward = pairs.rename(columns={
        "item_a": "anchor_item", "item_b": "recommended_item",
        "confidence_a_to_b": "confidence",
    })[["anchor_item", "recommended_item", "confidence", "lift", "pair_count"]]
    backward = pairs.rename(columns={
        "item_b": "anchor_item", "item_a": "recommended_item",
        "confidence_b_to_a": "confidence",
    })[["anchor_item", "recommended_item", "confidence", "lift", "pair_count"]]

    both = pd.concat([forward, backward], ignore_index=True)
    both = both[both["lift"] > 1.1]      # recommend only genuine associations
    both["rank"] = both.groupby("anchor_item")["lift"].rank(
        ascending=False, method="first"
    )
    return (
        both[both["rank"] <= top_n]
        .sort_values(["anchor_item", "rank"])
        .reset_index(drop=True)
    )


def basket_summary(lines: pd.DataFrame | None = None) -> pd.DataFrame:
    """Basket size distribution - the context every affinity number needs."""
    lines = datasets.sales_lines() if lines is None else lines
    per_order = lines.groupby("order_id").agg(
        distinct_items=("product_id", "nunique"),
        units=("quantity", "sum"),
        revenue=("net_amount", "sum"),
    )
    distribution = (
        per_order.groupby("distinct_items")
        .agg(orders=("units", "count"),
             avg_units=("units", "mean"),
             avg_revenue=("revenue", "mean"))
        .round(2)
        .reset_index()
    )
    distribution["share_of_orders_pct"] = (
        distribution["orders"] / distribution["orders"].sum() * 100
    ).round(1)
    return distribution


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Market-basket analysis")
    parser.add_argument("--min-support", type=float, default=0.002)
    parser.add_argument("--min-pair-count", type=int, default=3)
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args(argv)

    print(banner("PulseAnalytics - market basket analysis"))
    lines = datasets.sales_lines()

    print("\nBasket size distribution")
    print(basket_summary(lines).to_string(index=False))

    print("\nCategory affinity (sorted by lift)")
    categories = category_affinity(lines)
    print(categories.head(args.top).to_string(index=False) if not categories.empty
          else "Not enough multi-category baskets.")

    baskets = build_baskets(lines)
    pairs = affinity_pairs(baskets, args.min_support, args.min_pair_count)
    print(f"\nProduct affinity - {len(baskets):,} multi-item baskets, "
          f"{len(pairs):,} qualifying pairs")
    if pairs.empty:
        print("No product pair clears the support floor. Lower --min-support, "
              "or run the generator with a larger preset.")
    else:
        print(pairs.head(args.top).to_string(index=False))
        print("\nCross-sell recommendations")
        print(cross_sell_recommendations(pairs).head(args.top).to_string(index=False))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
