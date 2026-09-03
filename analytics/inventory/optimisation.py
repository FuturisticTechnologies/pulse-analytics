"""Inventory optimisation.

Turns the stock position in ``gold.mart_inventory_health`` into decisions:

* **Safety stock** - z x sigma_demand x sqrt(lead_time), the standard formula.
  It is driven by demand *variability*, not demand *level*, which is the point
  most spreadsheet reorder policies miss: a high-volume, perfectly steady
  product needs less buffer than a low-volume erratic one.
* **Reorder point** - average demand over the lead time, plus safety stock.
* **Economic order quantity** - the classic square-root trade-off between order
  cost and holding cost.
* **ABC x XYZ** - value class crossed with demand-predictability class. ABC
  alone tells you what matters; XYZ tells you how hard it is to plan. The grid
  is what actually determines a stocking policy.
* **Excess and dead stock** - working capital to release, with a number attached.

Service level is the one genuinely commercial input, so it is a parameter rather
than a constant: 95% is a reasonable default, 99% costs materially more stock.

    python -m analytics.inventory.optimisation --service-level 0.95
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from analytics.common import datasets
from pulse.db import get_database
from pulse.logging_utils import banner, get_logger

log = get_logger("analytics.inventory")

# Standard normal quantiles for the usual service levels.
Z_SCORES = {0.80: 0.84, 0.90: 1.28, 0.95: 1.65, 0.98: 2.05, 0.99: 2.33}

DEFAULT_LEAD_TIME_WEEKS = 2.0
ORDER_COST = 75.0            # cost to place and receive one purchase order
HOLDING_RATE = 0.22          # annual holding cost as a share of unit cost


def weekly_demand_stats() -> pd.DataFrame:
    """Mean and standard deviation of weekly units sold, per product.

    Straight from the snapshot fact, so the variability figure is measured
    rather than assumed.
    """
    return get_database().query("""
        SELECT
            f.product_key,
            f.product_id,
            COUNT(*)                                            AS weeks_observed,
            ROUND(AVG(CAST(f.units_sold AS DOUBLE PRECISION)), 3) AS mean_weekly_demand,
            ROUND(STDDEV_SAMP(CAST(f.units_sold AS DOUBLE PRECISION)), 3) AS sd_weekly_demand,
            MAX(f.units_sold)                                   AS max_weekly_demand,
            SUM(f.units_sold)                                   AS total_units
        FROM gold.fact_inventory f
        WHERE f.product_key <> -1
        GROUP BY f.product_key, f.product_id
    """)


def optimise(service_level: float = 0.95,
             lead_time_weeks: float = DEFAULT_LEAD_TIME_WEEKS) -> pd.DataFrame:
    """Recommended safety stock, reorder point and order quantity per product."""
    z = Z_SCORES.get(round(service_level, 2), 1.65)

    stock = datasets.inventory()
    demand = weekly_demand_stats()
    # ABC lives on the product-performance mart (it is a revenue classification,
    # not a stock one) - joined in rather than recomputed so both dashboards
    # show the same class for the same product.
    abc = datasets.products()[["product_key", "abc_class", "performance_segment"]]
    frame = (
        stock.merge(demand, on=["product_key", "product_id"], how="left")
             .merge(abc, on="product_key", how="left")
    )

    frame["mean_weekly_demand"] = frame["mean_weekly_demand"].fillna(0.0)
    frame["sd_weekly_demand"] = frame["sd_weekly_demand"].fillna(0.0)

    # ---- safety stock and reorder point
    frame["safety_stock"] = np.ceil(
        z * frame["sd_weekly_demand"] * np.sqrt(lead_time_weeks)
    ).astype(int)
    frame["lead_time_demand"] = np.ceil(
        frame["mean_weekly_demand"] * lead_time_weeks
    ).astype(int)
    frame["recommended_reorder_point"] = (
        frame["lead_time_demand"] + frame["safety_stock"]
    )

    # ---- economic order quantity: sqrt(2 D S / H)
    annual_demand = frame["mean_weekly_demand"] * 52.0
    holding_cost = (frame["unit_cost"].fillna(0) * HOLDING_RATE).replace(0, np.nan)
    frame["economic_order_qty"] = np.ceil(
        np.sqrt(2 * annual_demand * ORDER_COST / holding_cost)
    ).fillna(0).astype(int)
    frame["orders_per_year"] = np.where(
        frame["economic_order_qty"] > 0,
        (annual_demand / frame["economic_order_qty"]).round(1),
        0.0,
    )

    # ---- XYZ: how predictable is demand (coefficient of variation)
    coefficient_of_variation = np.where(
        frame["mean_weekly_demand"] > 0,
        frame["sd_weekly_demand"] / frame["mean_weekly_demand"],
        np.inf,
    )
    frame["demand_cv"] = np.round(coefficient_of_variation, 2)
    frame["xyz_class"] = np.select(
        [coefficient_of_variation <= 0.5,
         coefficient_of_variation <= 1.0],
        ["X", "Y"], default="Z",
    )
    frame["abc_xyz"] = frame["abc_class"].fillna("C") + frame["xyz_class"]

    # ---- the gap between policy and reality
    frame["reorder_point_gap"] = (
        frame["recommended_reorder_point"] - frame["reorder_point"]
    )
    frame["units_to_order"] = np.where(
        frame["on_hand_units"] <= frame["recommended_reorder_point"],
        np.maximum(frame["economic_order_qty"],
                   frame["recommended_reorder_point"] - frame["on_hand_units"]),
        0,
    ).astype(int)
    frame["order_value_at_cost"] = (
        frame["units_to_order"] * frame["unit_cost"].fillna(0)
    ).round(2)

    frame["policy"] = np.select(
        [frame["abc_xyz"].isin(["AX", "AY"]),
         frame["abc_xyz"] == "AZ",
         frame["abc_xyz"].str.startswith("B"),
         frame["abc_xyz"] == "CZ"],
        ["Tight control, frequent small orders",
         "High safety stock, weekly review",
         "Periodic review, standard buffer",
         "Make-to-order or delist"],
        default="Low-touch, bulk orders",
    )
    return frame


def working_capital_opportunity(optimised: pd.DataFrame) -> pd.DataFrame:
    """Where cash is trapped, and how much of it.

    Two buckets, because they need different actions: overstock is a markdown
    decision, dead stock is a write-off or delist decision.
    """
    # Uses the mart's own flags, not a second set of thresholds invented here.
    # Two definitions of "overstocked" in one platform is how a dashboard and a
    # purchasing report end up disagreeing in a meeting.
    overstock = optimised[optimised["stock_status"] == "Overstocked - markdown"]
    dead = optimised[optimised["stock_status"] == "Dead stock"]

    excess_units = (
        overstock["on_hand_units"] - overstock["recommended_reorder_point"]
    ).clip(lower=0)

    return pd.DataFrame([
        {
            "bucket": "Overstocked (flagged by the inventory mart)",
            "products": len(overstock),
            "units": int(excess_units.sum()),
            "capital_at_cost": round(float((excess_units * overstock["unit_cost"]).sum()), 2),
            "action": "Markdown or transfer between locations",
        },
        {
            "bucket": "Dead stock (no sales in the tracked window)",
            "products": len(dead),
            "units": int(dead["on_hand_units"].sum()),
            "capital_at_cost": round(float(dead["on_hand_value_at_cost"].sum()), 2),
            "action": "Clearance, then delist",
        },
    ])


def abc_xyz_grid(optimised: pd.DataFrame) -> pd.DataFrame:
    grid = optimised.pivot_table(
        index="abc_class", columns="xyz_class", values="product_id",
        aggfunc="count", fill_value=0,
    )
    return grid.reset_index()


def reorder_list(optimised: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """The purchase order, in the order it should be raised."""
    due = optimised[optimised["units_to_order"] > 0].copy()
    return (
        due.sort_values(["action_priority", "order_value_at_cost"],
                        ascending=[True, False])
        [["sku", "product_name", "category", "abc_xyz", "on_hand_units",
          "reorder_point", "recommended_reorder_point", "safety_stock",
          "units_to_order", "order_value_at_cost", "stock_status", "policy"]]
        .head(top_n)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inventory optimisation")
    parser.add_argument("--service-level", type=float, default=0.95,
                        choices=sorted(Z_SCORES))
    parser.add_argument("--lead-time-weeks", type=float, default=DEFAULT_LEAD_TIME_WEEKS)
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args(argv)

    print(banner("PulseAnalytics - inventory optimisation"))
    optimised = optimise(args.service_level, args.lead_time_weeks)
    log.info("service level %.0f%% (z=%.2f), lead time %.1f weeks",
             args.service_level * 100, Z_SCORES[round(args.service_level, 2)],
             args.lead_time_weeks)

    print("\nABC x XYZ grid (rows = revenue class, columns = demand predictability)")
    print(abc_xyz_grid(optimised).to_string(index=False))

    print("\nStock status")
    print(optimised.groupby("stock_status").agg(
        products=("product_id", "count"),
        on_hand_value=("on_hand_value_at_cost", "sum"),
    ).round(2).reset_index().to_string(index=False))

    print("\nWorking capital opportunity")
    print(working_capital_opportunity(optimised).to_string(index=False))

    print(f"\nReorder list ({int((optimised['units_to_order'] > 0).sum())} products due)")
    print(reorder_list(optimised, args.top).to_string(index=False))

    total = optimised["order_value_at_cost"].sum()
    print(f"\nTotal recommended purchase value: {total:,.2f}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
