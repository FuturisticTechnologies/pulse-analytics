"""Revenue and demand forecasting.

Two models, both fitted on numpy alone:

* **Holt-Winters (triple exponential smoothing)** with additive seasonality -
  level + trend + repeating shape, which is exactly the structure retail revenue
  has. Weekly seasonality for the daily series, yearly for the monthly one.
* **Seasonal naive** - "next week looks like last week". Present as the
  *baseline*, not as filler: a forecast that cannot beat seasonal naive on a
  backtest is not a forecast, and reporting only the sophisticated model's error
  hides that.

Everything is **backtested by holding out the tail of the actual history**, never
scored on data it was fitted to. Reported with MAE, RMSE, MAPE and bias -- bias
in particular, because a model that is consistently 8% low is a very different
operational problem from one that is noisily wrong.

Forecasts are published with an 80% prediction interval. A single line implies
a precision no revenue forecast has.

    python -m analytics.forecasting.forecast --horizon 60
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from analytics.common import datasets
from analytics.common.modelling import (
    forecast_accuracy,
    holt_winters_additive,
    linear_trend,
    prediction_interval,
)
from pulse.logging_utils import banner, get_logger

log = get_logger("analytics.forecast")


# --------------------------------------------------------------------------- #
# Baselines
# --------------------------------------------------------------------------- #
def seasonal_naive(values: np.ndarray, season_length: int, horizon: int) -> np.ndarray:
    """Repeat the most recent complete season forward."""
    if len(values) < season_length:
        return np.full(horizon, float(values[-1]) if len(values) else 0.0)
    last_season = values[-season_length:]
    repeats = int(np.ceil(horizon / season_length))
    return np.tile(last_season, repeats)[:horizon]


def trend_forecast(values: np.ndarray, horizon: int) -> np.ndarray:
    slope, intercept = linear_trend(values)
    n = len(values)
    return np.maximum(intercept + slope * np.arange(n, n + horizon), 0.0)


# --------------------------------------------------------------------------- #
# Backtesting
# --------------------------------------------------------------------------- #
def backtest(values: np.ndarray, season_length: int,
             holdout: int) -> pd.DataFrame:
    """Fit on everything except the last ``holdout`` points; score on those."""
    if len(values) <= holdout + season_length:
        raise ValueError("not enough history to backtest with that holdout")

    train, test = values[:-holdout], values[-holdout:]
    candidates = {
        "holt_winters": holt_winters_additive(train, season_length, holdout)[1],
        "seasonal_naive": seasonal_naive(train, season_length, holdout),
        "linear_trend": trend_forecast(train, holdout),
    }

    rows = []
    for name, predicted in candidates.items():
        metrics = forecast_accuracy(test, predicted)
        rows.append({"model": name, "holdout_points": holdout, **metrics})

    result = pd.DataFrame(rows).sort_values("mape_pct").reset_index(drop=True)
    result["is_best"] = result.index == 0
    # Explicitly say whether the sophisticated model earned its place.
    naive_mape = float(result.loc[result["model"] == "seasonal_naive", "mape_pct"].iloc[0])
    result["vs_naive_pct"] = (
        (result["mape_pct"] - naive_mape) / max(naive_mape, 1e-9) * 100
    ).round(1)
    return result


# --------------------------------------------------------------------------- #
# Forecasts
# --------------------------------------------------------------------------- #
def forecast_daily_revenue(horizon: int = 60, holdout: int = 28,
                           confidence: float = 0.80) -> dict:
    """Daily revenue forecast with weekly seasonality."""
    daily = datasets.daily_sales()
    series = daily.set_index("order_date")["revenue"].astype(float)
    values = series.to_numpy()

    scores = backtest(values, season_length=7, holdout=holdout)
    best_model = scores.loc[0, "model"]

    fitted, forecast = holt_winters_additive(values, season_length=7, horizon=horizon)
    if best_model == "seasonal_naive":
        forecast = seasonal_naive(values, 7, horizon)
    elif best_model == "linear_trend":
        forecast = trend_forecast(values, horizon)

    residuals = values - fitted
    half_width = prediction_interval(residuals, horizon, confidence)

    future_dates = pd.date_range(
        series.index.max() + pd.Timedelta(days=1), periods=horizon, freq="D"
    )
    frame = pd.DataFrame({
        "date": future_dates,
        "forecast": np.round(forecast, 2),
        "lower": np.round(np.maximum(forecast - half_width, 0), 2),
        "upper": np.round(forecast + half_width, 2),
    })
    log.info("daily forecast: %s model, %d days, total %.0f",
             best_model, horizon, frame["forecast"].sum())
    return {
        "forecast": frame,
        "backtest": scores,
        "model": best_model,
        "history": series.reset_index().rename(columns={"order_date": "date"}),
        "confidence": confidence,
    }


def forecast_monthly_revenue(horizon: int = 6, holdout: int = 4,
                             confidence: float = 0.80) -> dict:
    """Monthly revenue forecast.

    The final month of the mart is usually partial (the data ends mid-month), so
    it is dropped before fitting: a half month read as a full one tells the model
    the business just halved.
    """
    monthly = datasets.monthly_sales()
    complete = monthly.iloc[:-1] if len(monthly) > 2 else monthly
    series = complete.set_index("month_start")["revenue"].astype(float)
    values = series.to_numpy()

    season_length = 12 if len(values) >= 24 else 3
    try:
        scores = backtest(values, season_length=season_length, holdout=holdout)
        best_model = scores.loc[0, "model"]
    except ValueError:
        scores = pd.DataFrame()
        best_model = "holt_winters"

    fitted, forecast = holt_winters_additive(values, season_length, horizon)
    if best_model == "seasonal_naive":
        forecast = seasonal_naive(values, season_length, horizon)
    elif best_model == "linear_trend":
        forecast = trend_forecast(values, horizon)

    half_width = prediction_interval(values - fitted, horizon, confidence)
    future_months = pd.date_range(
        series.index.max() + pd.offsets.MonthBegin(1), periods=horizon, freq="MS"
    )
    frame = pd.DataFrame({
        "month_start": future_months,
        "forecast": np.round(forecast, 2),
        "lower": np.round(np.maximum(forecast - half_width, 0), 2),
        "upper": np.round(forecast + half_width, 2),
    })
    return {
        "forecast": frame, "backtest": scores, "model": best_model,
        "history": series.reset_index(), "confidence": confidence,
        "excluded_partial_month": len(monthly) > len(complete),
    }


def forecast_category_demand(horizon_weeks: int = 8) -> pd.DataFrame:
    """Per-category unit demand, for the purchasing plan.

    Falls back to the category's trailing mean where there is not enough
    history for a seasonal fit - and says so in the ``method`` column rather
    than quietly producing a flat line that looks like a model output.
    """
    lines = datasets.sales_lines()
    lines["order_date"] = pd.to_datetime(lines["order_date"])
    lines["week_start"] = lines["order_date"] - pd.to_timedelta(
        lines["order_date"].dt.dayofweek, unit="D"
    )
    weekly = (
        lines.groupby(["category", "week_start"])["quantity"].sum()
        .reset_index().sort_values(["category", "week_start"])
    )

    rows = []
    for category, group in weekly.groupby("category"):
        values = group["quantity"].to_numpy(dtype=float)
        if len(values) >= 8:
            _fitted, forecast = holt_winters_additive(values, season_length=4,
                                                      horizon=horizon_weeks)
            method = "holt_winters"
        else:
            forecast = np.full(horizon_weeks, values.mean() if len(values) else 0.0)
            method = "trailing_mean (insufficient history)"

        future_weeks = pd.date_range(
            group["week_start"].max() + pd.Timedelta(weeks=1),
            periods=horizon_weeks, freq="W-MON",
        )
        for week, units in zip(future_weeks, forecast):
            rows.append({
                "category": category, "week_start": week,
                "forecast_units": int(round(max(units, 0))), "method": method,
            })
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Forecast revenue and demand")
    parser.add_argument("--horizon", type=int, default=60, help="days to forecast")
    parser.add_argument("--holdout", type=int, default=28, help="backtest holdout in days")
    parser.add_argument("--months", type=int, default=6)
    args = parser.parse_args(argv)

    print(banner("PulseAnalytics - forecasting"))

    daily = forecast_daily_revenue(args.horizon, args.holdout)
    print(f"\nDaily revenue backtest (last {args.holdout} days held out)")
    print(daily["backtest"].to_string(index=False))
    print(f"\nSelected model: {daily['model']}")
    print(f"\nNext {args.horizon} days ({int(daily['confidence'] * 100)}% interval)")
    print(daily["forecast"].head(14).to_string(index=False))
    print(f"...\nForecast total over the horizon: "
          f"{daily['forecast']['forecast'].sum():,.2f} "
          f"({daily['forecast']['lower'].sum():,.0f} - "
          f"{daily['forecast']['upper'].sum():,.0f})")

    monthly = forecast_monthly_revenue(args.months)
    print(f"\nMonthly revenue forecast - model: {monthly['model']}")
    if monthly["excluded_partial_month"]:
        print("(the final, partial month of history was excluded from the fit)")
    print(monthly["forecast"].to_string(index=False))

    print("\nCategory demand, next 8 weeks (units)")
    category = forecast_category_demand()
    print(category.pivot_table(index="category", columns="week_start",
                               values="forecast_units", aggfunc="sum")
          .to_string())
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
