"""Marketing attribution and campaign economics.

The warehouse ships **last-touch** attribution, because that is what the source
system records. This module makes that limitation explicit and then shows what
changes under other models, using the clickstream that precedes each order:

    first_touch   all credit to the first channel in the journey
    last_touch    all credit to the last (the warehouse default)
    linear        credit split evenly across every touch
    time_decay    credit weighted towards touches nearer the conversion
    position      40% first, 40% last, 20% split across the middle

No model is "correct". Publishing several side by side is the honest treatment,
and the spread between them is itself the finding: where first-touch and
last-touch disagree sharply, an upper-funnel channel is being starved by a
last-touch budget.

Also computes the campaign economics that decide budget: ROAS, profit ROAS,
CAC, payback period, and an incrementality proxy.

    python -m analytics.marketing.attribution
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from analytics.common import datasets
from pulse.db import get_database
from pulse.logging_utils import banner, get_logger

log = get_logger("analytics.attribution")

LOOKBACK_DAYS = 30      # how far back a touch can be and still get credit


def _journeys() -> pd.DataFrame:
    """Build converting journeys: the touches preceding each purchase.

    A "touch" here is a session, attributed to the marketing channel that was
    running when it happened. With only campaign-window data available, channel
    assignment is by active campaign - approximate, and stated as such.
    """
    db = get_database()
    return db.query(f"""
        WITH purchases AS (
            SELECT o.order_key, o.customer_key, o.order_ts, o.order_date, o.net_amount
            FROM gold.fact_orders o
            WHERE o.is_revenue
        ),
        touches AS (
            SELECT
                e.customer_key,
                e.session_id,
                MIN(e.event_ts)     AS touch_ts,
                MIN(e.event_date)   AS touch_date
            FROM gold.fact_customer_events e
            WHERE e.customer_key <> -1
            GROUP BY e.customer_key, e.session_id
        ),
        channelled AS (
            SELECT
                t.customer_key,
                t.session_id,
                t.touch_ts,
                COALESCE(
                    (SELECT c.channel
                     FROM gold.dim_campaign c
                     WHERE c.campaign_key <> -1
                       AND t.touch_date BETWEEN c.start_date AND c.end_date
                     ORDER BY c.spend DESC
                     LIMIT 1),
                    'Organic'
                ) AS channel
            FROM touches t
        )
        SELECT
            p.order_key,
            p.customer_key,
            p.net_amount,
            p.order_ts,
            ch.channel,
            ch.touch_ts,
            CAST(EXTRACT(EPOCH FROM (p.order_ts - ch.touch_ts)) / 86400.0 AS DOUBLE PRECISION)
                AS days_before_order
        FROM purchases p
        JOIN channelled ch
          ON ch.customer_key = p.customer_key
         AND ch.touch_ts <= p.order_ts
         AND ch.touch_ts >= p.order_ts - INTERVAL '{LOOKBACK_DAYS} days'
    """)


def attribute(journeys: pd.DataFrame | None = None) -> pd.DataFrame:
    """Credit each order's revenue to channels under five models."""
    journeys = _journeys() if journeys is None else journeys
    if journeys.empty:
        log.warning("no converting journeys found within the %d-day lookback", LOOKBACK_DAYS)
        return pd.DataFrame(columns=["channel", "first_touch", "last_touch",
                                     "linear", "time_decay", "position_based"])

    journeys = journeys.sort_values(["order_key", "touch_ts"])
    credits: list[dict] = []

    for order_key, group in journeys.groupby("order_key", sort=False):
        revenue = float(group["net_amount"].iloc[0])
        channels = group["channel"].tolist()
        n = len(channels)

        # ---- first / last
        weights = {
            "first_touch": np.eye(n)[0] if n else np.array([]),
            "last_touch": np.eye(n)[-1] if n else np.array([]),
            "linear": np.full(n, 1.0 / n) if n else np.array([]),
        }

        # ---- time decay: half-life of 7 days before the conversion
        days = group["days_before_order"].to_numpy(dtype=float)
        decay = 0.5 ** (days / 7.0)
        weights["time_decay"] = decay / decay.sum() if decay.sum() else np.full(n, 1.0 / n)

        # ---- position based: 40 / 20 / 40
        position = np.zeros(n)
        if n == 1:
            position[0] = 1.0
        elif n == 2:
            position[0] = position[1] = 0.5
        else:
            position[0] = position[-1] = 0.4
            position[1:-1] = 0.2 / (n - 2)
        weights["position_based"] = position

        for index, channel in enumerate(channels):
            credits.append({
                "order_key": order_key,
                "channel": channel,
                **{model: revenue * weight[index] for model, weight in weights.items()},
            })

    frame = pd.DataFrame(credits)
    result = frame.groupby("channel")[
        ["first_touch", "last_touch", "linear", "time_decay", "position_based"]
    ].sum().round(2)

    # The disagreement between models is the actionable part.
    result["upper_funnel_bias"] = (
        result["first_touch"] - result["last_touch"]
    ).round(2)
    result["share_last_touch_pct"] = (
        result["last_touch"] / result["last_touch"].sum() * 100
    ).round(1)
    result["share_linear_pct"] = (
        result["linear"] / result["linear"].sum() * 100
    ).round(1)
    return result.sort_values("linear", ascending=False).reset_index()


def campaign_economics() -> pd.DataFrame:
    """Campaign-level economics with payback, from the gold mart."""
    campaigns = datasets.campaigns()
    if campaigns.empty:
        return campaigns

    campaigns = campaigns.copy()
    daily_profit = campaigns["gross_profit"] / campaigns["duration_days"].clip(lower=1)
    campaigns["payback_days"] = np.where(
        daily_profit > 0,
        (campaigns["spend"] / daily_profit).round(1),
        np.nan,
    )
    campaigns["profit_per_customer"] = (
        campaigns["gross_profit"] / campaigns["customers"].replace(0, np.nan)
    ).round(2)
    campaigns["efficiency_rank"] = campaigns["profit_roas"].rank(
        ascending=False, method="min"
    ).astype(int)
    return campaigns.sort_values("profit_roas", ascending=False)


def budget_reallocation(top_n: int = 5) -> pd.DataFrame:
    """A concrete, defensible budget move.

    Takes 25% of the spend on channels whose profit ROAS is below 1.0 (they lose
    money on every incremental dollar) and reallocates it to the channels above
    1.0, in proportion to their profit ROAS. The projected gain assumes the
    receiving channel holds its current efficiency at the margin - an assumption
    stated on the output because it is the one that will be wrong first.
    """
    channels = get_database().query(
        "SELECT * FROM gold.mart_channel_performance ORDER BY profit_roas DESC"
    )
    if channels.empty:
        return channels

    losers = channels[channels["profit_roas"] < 1.0].copy()
    winners = channels[channels["profit_roas"] >= 1.0].copy()
    if losers.empty or winners.empty:
        channels["recommended_change"] = 0.0
        channels["note"] = "No reallocation: every channel is on the same side of break-even."
        return channels

    freed = float((losers["spend"] * 0.25).sum())
    winners["weight"] = winners["profit_roas"] / winners["profit_roas"].sum()
    winners["recommended_change"] = (winners["weight"] * freed).round(2)
    losers["recommended_change"] = (-losers["spend"] * 0.25).round(2)

    combined = pd.concat([winners.drop(columns="weight"), losers], ignore_index=True)
    combined["new_spend"] = (combined["spend"] + combined["recommended_change"]).round(2)
    combined["projected_profit_change"] = (
        combined["recommended_change"] * combined["profit_roas"]
    ).round(2)
    combined["note"] = np.where(
        combined["recommended_change"] > 0, "Scale up", "Cut back"
    )
    return combined[[
        "channel", "spend", "profit_roas", "recommended_change", "new_spend",
        "projected_profit_change", "note",
    ]].sort_values("recommended_change", ascending=False).head(top_n + len(losers))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Marketing attribution and economics")
    parser.add_argument("--top", type=int, default=12)
    args = parser.parse_args(argv)

    print(banner("PulseAnalytics - marketing attribution"))

    models = attribute()
    print(f"\nRevenue credited by attribution model (lookback {LOOKBACK_DAYS} days)")
    print(models.to_string(index=False) if not models.empty
          else "No converting journeys in the clickstream window.")
    if not models.empty:
        print("\nPositive upper_funnel_bias = the channel is under-credited by "
              "last-touch and is being under-funded.")

    economics = campaign_economics()
    print("\nCampaign economics (best profit ROAS first)")
    print(economics[["campaign_name", "channel", "spend", "revenue", "gross_profit",
                     "roas", "profit_roas", "cac", "payback_days", "verdict"]]
          .head(args.top).to_string(index=False))

    print("\nSuggested budget reallocation (25% of below-break-even spend)")
    print(budget_reallocation().to_string(index=False))
    print("\nAssumes receiving channels hold their current marginal efficiency.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
