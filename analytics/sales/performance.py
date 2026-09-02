"""Sales performance analysis.

Goes past "revenue went up" to *why* it went up, which is the only version of
the answer anyone can act on.

* **Seasonality decomposition** - separates trend, weekly shape and residual so
  a Tuesday dip is not escalated as a problem.
* **Price / volume / mix bridge** - decomposes a revenue change between two
  periods into how much came from selling more, charging more, and shifting the
  category mix. Additive by construction, so the three components always sum to
  the total change.
* **Anomaly detection** - flags days whose residual is more than 2.5 robust
  standard deviations from the trend, using MAD rather than sigma so a single
  Black Friday does not raise the bar for the entire year.

    python -m analytics.sales.performance
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from analytics.common import datasets
from analytics.common.modelling import linear_trend
from pulse.logging_utils import banner, get_logger

log = get_logger("analytics.sales")


# --------------------------------------------------------------------------- #
# Seasonality
# --------------------------------------------------------------------------- #
def decompose_daily(frame: pd.DataFrame | None = None,
                    window: int = 7) -> pd.DataFrame:
    """Classic additive decomposition: value = trend + seasonal + residual.

    Trend is a centred moving average (window = one week), seasonal is the mean
    detrended value per weekday, residual is what is left. Written out rather
    than imported so the reader can see there is no magic in it.
    """
    frame = datasets.daily_sales() if frame is None else frame.copy()
    frame = frame.sort_values("order_date").reset_index(drop=True)

    series = frame["revenue"].astype(float)
    frame["trend"] = series.rolling(window, center=True, min_periods=1).mean().round(2)
    frame["detrended"] = (series - frame["trend"]).round(2)

    weekday = frame["order_date"].dt.dayofweek
    seasonal_by_weekday = frame.groupby(weekday)["detrended"].mean()
    # Centre the seasonal component so it redistributes rather than shifts.
    seasonal_by_weekday = seasonal_by_weekday - seasonal_by_weekday.mean()
    frame["seasonal"] = weekday.map(seasonal_by_weekday).round(2)
    frame["residual"] = (series - frame["trend"] - frame["seasonal"]).round(2)
    return frame


def weekday_profile(frame: pd.DataFrame | None = None) -> pd.DataFrame:
    """How much each weekday over- or under-performs the average day."""
    frame = datasets.daily_sales() if frame is None else frame.copy()
    frame["weekday"] = frame["order_date"].dt.day_name()
    frame["weekday_number"] = frame["order_date"].dt.dayofweek

    profile = frame.groupby(["weekday_number", "weekday"]).agg(
        days=("revenue", "count"),
        avg_revenue=("revenue", "mean"),
        avg_orders=("orders_completed", "mean"),
        avg_order_value=("avg_order_value", "mean"),
    ).round(2).reset_index()
    overall = frame["revenue"].mean()
    profile["index_vs_average"] = (profile["avg_revenue"] / overall * 100).round(1)
    return profile.sort_values("weekday_number").drop(columns="weekday_number")


def monthly_seasonality(frame: pd.DataFrame | None = None) -> pd.DataFrame:
    """Month-of-year index. Needs two years of history to be trustworthy, and
    reports how many years each month was observed so the reader can judge."""
    frame = datasets.daily_sales() if frame is None else frame.copy()
    frame["month"] = frame["order_date"].dt.month
    frame["month_name"] = frame["order_date"].dt.strftime("%b")

    monthly = frame.groupby(["month", "month_name"]).agg(
        avg_daily_revenue=("revenue", "mean"),
        total_revenue=("revenue", "sum"),
        years_observed=("order_date", lambda s: s.dt.year.nunique()),
    ).round(2).reset_index()
    monthly["seasonal_index"] = (
        monthly["avg_daily_revenue"] / frame["revenue"].mean() * 100
    ).round(1)
    return monthly.sort_values("month").drop(columns="month")


# --------------------------------------------------------------------------- #
# Growth decomposition
# --------------------------------------------------------------------------- #
def price_volume_mix(period_days: int = 90) -> pd.DataFrame:
    """Split the revenue change between the last two periods into its drivers.

    Per category, revenue is exactly price x units, so only two effects exist:

        volume effect = (units_now - units_before) x price_before
        price  effect = (price_now - price_before) x units_now

    MIX only exists at the total, where it captures revenue moved by customers
    shifting between categories of different average price. It is therefore
    computed once, at the total line, as the residual:

        mix = total revenue change - sum(volume effects) - sum(price effects)

    Reporting a per-category "mix" would be reporting a column of zeros and
    calling it insight.
    """
    lines = datasets.sales_lines()
    lines["order_date"] = pd.to_datetime(lines["order_date"])
    latest = lines["order_date"].max()

    current_start = latest - pd.Timedelta(days=period_days - 1)
    prior_start = current_start - pd.Timedelta(days=period_days)

    current = lines[lines["order_date"] >= current_start]
    prior = lines[(lines["order_date"] >= prior_start) &
                  (lines["order_date"] < current_start)]

    def summarise(chunk: pd.DataFrame, suffix: str) -> pd.DataFrame:
        grouped = chunk.groupby("category").agg(
            **{f"revenue_{suffix}": ("net_amount", "sum"),
               f"units_{suffix}": ("quantity", "sum")}
        )
        grouped[f"price_{suffix}"] = (
            grouped[f"revenue_{suffix}"] / grouped[f"units_{suffix}"].replace(0, np.nan)
        )
        return grouped

    merged = summarise(prior, "prior").join(
        summarise(current, "current"), how="outer"
    ).fillna(0)

    merged["revenue_change"] = merged["revenue_current"] - merged["revenue_prior"]
    merged["volume_effect"] = (
        (merged["units_current"] - merged["units_prior"]) * merged["price_prior"]
    )
    merged["price_effect"] = (
        (merged["price_current"] - merged["price_prior"]) * merged["units_current"]
    )
    merged["mix_effect"] = 0.0      # zero within a category, by construction

    result = merged.round(2).reset_index()

    # ---- total line, where mix genuinely lives -----------------------------
    units_prior = float(merged["units_prior"].sum())
    units_current = float(merged["units_current"].sum())
    revenue_prior = float(merged["revenue_prior"].sum())
    revenue_current = float(merged["revenue_current"].sum())
    blended_price_prior = revenue_prior / units_prior if units_prior else 0.0
    blended_price_current = revenue_current / units_current if units_current else 0.0

    total_volume = (units_current - units_prior) * blended_price_prior
    total_price = float(merged["price_effect"].sum())
    total_change = revenue_current - revenue_prior
    total_mix = total_change - total_volume - total_price

    total_row = {
        "category": "TOTAL",
        "revenue_prior": round(revenue_prior, 2),
        "revenue_current": round(revenue_current, 2),
        "units_prior": round(units_prior, 2),
        "units_current": round(units_current, 2),
        "price_prior": round(blended_price_prior, 2),
        "price_current": round(blended_price_current, 2),
        "revenue_change": round(total_change, 2),
        "volume_effect": round(total_volume, 2),
        "price_effect": round(total_price, 2),
        "mix_effect": round(total_mix, 2),
    }
    result = pd.concat([result, pd.DataFrame([total_row])], ignore_index=True)
    result.attrs["period_days"] = period_days
    result.attrs["current_start"] = current_start.date()
    return result


def growth_summary() -> pd.DataFrame:
    """Headline growth at three horizons, from the monthly mart."""
    monthly = datasets.monthly_sales()
    if len(monthly) < 2:
        return monthly

    latest = monthly.iloc[-1]
    rows = [{
        "metric": "Latest month revenue",
        "value": round(float(latest["revenue"]), 2),
        "vs_prev_month_pct": latest.get("revenue_mom_pct"),
        "vs_prev_year_pct": latest.get("revenue_yoy_pct"),
    }]

    slope, _intercept = linear_trend(monthly["revenue"].to_numpy())
    rows.append({
        "metric": "Trend (revenue change per month)",
        "value": round(slope, 2), "vs_prev_month_pct": None, "vs_prev_year_pct": None,
    })

    full_years = monthly[monthly["month_start"].dt.year.isin(
        monthly["month_start"].dt.year.unique()[-2:]
    )]
    by_year = full_years.groupby(full_years["month_start"].dt.year)["revenue"].sum()
    if len(by_year) >= 2:
        rows.append({
            "metric": f"{by_year.index[-1]} vs {by_year.index[-2]} revenue",
            "value": round(float(by_year.iloc[-1]), 2),
            "vs_prev_month_pct": None,
            "vs_prev_year_pct": round(
                float((by_year.iloc[-1] - by_year.iloc[-2]) / by_year.iloc[-2] * 100), 2
            ),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Anomalies
# --------------------------------------------------------------------------- #
def detect_anomalies(frame: pd.DataFrame | None = None,
                     threshold: float = 2.5) -> pd.DataFrame:
    """Flag days whose residual is extreme, scored in robust (MAD) units.

    Median absolute deviation rather than standard deviation: a handful of
    genuine peak-season spikes would inflate sigma enough to hide every ordinary
    anomaly for the rest of the year.
    """
    decomposed = decompose_daily(frame)
    residuals = decomposed["residual"].astype(float)
    median = residuals.median()
    mad = (residuals - median).abs().median()
    scale = mad * 1.4826 if mad > 0 else residuals.std()
    if not scale:
        return decomposed.head(0)

    decomposed["robust_z"] = ((residuals - median) / scale).round(2)
    flagged = decomposed[decomposed["robust_z"].abs() >= threshold].copy()
    flagged["direction"] = np.where(flagged["robust_z"] > 0, "spike", "dip")
    flagged["expected_revenue"] = (flagged["trend"] + flagged["seasonal"]).round(2)
    return flagged[[
        "order_date", "revenue", "expected_revenue", "residual", "robust_z",
        "direction", "orders_completed", "is_peak_season",
    ]].sort_values("order_date")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sales performance analysis")
    parser.add_argument("--period-days", type=int, default=90)
    args = parser.parse_args(argv)

    print(banner("PulseAnalytics - sales performance"))

    print("\nGrowth")
    print(growth_summary().to_string(index=False))

    print("\nDay-of-week profile (100 = average day)")
    print(weekday_profile().to_string(index=False))

    print("\nMonth-of-year seasonality (100 = average day)")
    print(monthly_seasonality().to_string(index=False))

    bridge = price_volume_mix(args.period_days)
    print(f"\nPrice / volume / mix bridge - last {args.period_days} days vs the "
          f"{args.period_days} before")
    print(bridge[["category", "revenue_prior", "revenue_current", "revenue_change",
                  "volume_effect", "price_effect", "mix_effect"]].to_string(index=False))

    anomalies = detect_anomalies()
    print(f"\nAnomalous trading days ({len(anomalies)} found)")
    print(anomalies.tail(12).to_string(index=False) if not anomalies.empty
          else "None outside 2.5 robust standard deviations.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
