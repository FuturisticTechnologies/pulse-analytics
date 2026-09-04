"""Run every analytical model and write the results to ``reports/``.

One command produces the analyst's deliverable: a markdown insight report plus
CSV extracts that a stakeholder can open in Excel or a BI tool without asking
anyone for database access.

    python -m analytics.run_analytics
    python -m analytics.run_analytics --only churn,forecast

Each model is run inside its own try/except. One failing model must not cost
you the other eight - the failure is reported in the output rather than
replacing it.
"""
from __future__ import annotations

import argparse
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

from analytics.common import datasets
from analytics.customer import churn, clv, segmentation
from analytics.forecasting import forecast
from analytics.inventory import optimisation
from analytics.marketing import attribution
from analytics.sales import basket, performance
from pulse.config import PATHS
from pulse.kpi import compact, money
from pulse.logging_utils import banner, get_logger

log = get_logger("analytics.run")

REPORT_DIR = PATHS.root / "reports"
EXPORT_DIR = PATHS.exports


def _write_csv(frame: pd.DataFrame, name: str) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPORT_DIR / f"{name}.csv"
    frame.to_csv(path, index=False)
    return path


def _table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame is None or frame.empty:
        return "_No rows._\n"
    return frame.head(max_rows).to_markdown(index=False) + "\n"


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def section_executive() -> str:
    from pulse.db import get_database

    kpis = get_database().query("SELECT * FROM gold.mart_executive_kpis").iloc[0]
    lines = [
        "## Executive summary",
        "",
        f"As of **{pd.to_datetime(kpis['as_of_date']):%Y-%m-%d}**, "
        f"trailing 90 days against the 90 before.",
        "",
        "| KPI | Value | Change |",
        "| --- | ---: | ---: |",
        f"| Revenue | {money(kpis['revenue_90d'])} | {kpis['revenue_change_pct']}% |",
        f"| Gross profit | {money(kpis['gross_profit_90d'])} | "
        f"{kpis['gross_margin_pct']}% margin |",
        f"| Orders | {compact(kpis['orders_90d'])} | {kpis['orders_change_pct']}% |",
        f"| Average order value | {money(kpis['avg_order_value'])} | "
        f"was {money(kpis['avg_order_value_prev'])} |",
        f"| Active customers | {compact(kpis['active_customers_90d'])} | "
        f"{compact(kpis['new_customers_90d'])} new |",
        f"| Repeat rate | {kpis['repeat_rate_pct']}% | "
        f"churn {kpis['churn_rate_pct']}% |",
        f"| Blended ROAS | {kpis['blended_roas']} | "
        f"CAC {money(kpis['blended_cac'])} |",
        f"| Payment failure rate | {kpis['payment_failure_rate_pct']}% | "
        f"{money(kpis['payment_amount_at_risk'])} at risk |",
        f"| Products below reorder | {int(kpis['products_below_reorder'])} | "
        f"{int(kpis['products_stocked_out'])} stocked out |",
        "",
    ]
    return "\n".join(lines)


def section_sales() -> str:
    weekday = performance.weekday_profile()
    seasonal = performance.monthly_seasonality()
    bridge = performance.price_volume_mix(90)
    anomalies = performance.detect_anomalies()

    _write_csv(bridge, "sales_price_volume_mix")
    _write_csv(anomalies, "sales_anomalies")

    total = bridge[bridge["category"] == "TOTAL"].iloc[0]
    direction = "grew" if total["revenue_change"] >= 0 else "fell"
    best_day = weekday.loc[weekday["index_vs_average"].idxmax()]
    peak_month = seasonal.loc[seasonal["seasonal_index"].idxmax()]

    return "\n".join([
        "## Sales",
        "",
        f"Revenue {direction} by **{money(abs(total['revenue_change']))}** over the last "
        f"90 days versus the 90 before. Decomposed: "
        f"volume {money(total['volume_effect'])}, price {money(total['price_effect'])}, "
        f"category mix {money(total['mix_effect'])}.",
        "",
        f"The strongest trading day is **{best_day['weekday']}** at "
        f"{best_day['index_vs_average']}% of an average day; the strongest month is "
        f"**{peak_month['month_name']}** at {peak_month['seasonal_index']}%.",
        "",
        "### Price / volume / mix bridge",
        "",
        _table(bridge[["category", "revenue_prior", "revenue_current", "revenue_change",
                       "volume_effect", "price_effect", "mix_effect"]]),
        "### Day-of-week profile",
        "",
        _table(weekday),
        f"### Anomalous trading days ({len(anomalies)} beyond 2.5 robust SD)",
        "",
        _table(anomalies.tail(10)),
    ])


def section_customers() -> str:
    segments = segmentation.segment_customers(k=5)
    clv_scores = clv.compute_clv()
    ratios = clv.ltv_to_cac(clv_scores)
    churn_model = churn.fit_churn_model()
    risk = churn.score_current_customers(churn_model)
    risk_bands = churn.risk_summary(risk)

    _write_csv(segments["profile"], "customer_segments")
    _write_csv(clv_scores[["customer_id", "full_name", "orders", "lifetime_revenue",
                           "historic_clv", "predicted_clv", "total_clv", "clv_decile"]],
               "customer_clv")
    _write_csv(risk[["customer_id", "full_name", "loyalty_tier", "recency_days",
                     "orders", "lifetime_revenue", "churn_probability",
                     "risk_band", "revenue_at_risk"]].head(500),
               "customer_churn_risk")

    at_risk_value = float(risk_bands.loc[
        risk_bands["risk_band"].isin(["High", "Critical"]), "revenue_at_risk"
    ].sum())
    metrics = churn_model["metrics"].iloc[0]
    top_driver = churn_model["coefficients"].iloc[0]

    return "\n".join([
        "## Customers",
        "",
        f"k-means finds **{len(segments['profile'])}** behavioural segments; the "
        f"cross-tab against the SQL RFM grid is in "
        f"`data/exports/customer_segments.csv`.",
        "",
        f"The churn model scores **{metrics['holdout_auc']}** AUC on a held-out "
        f"split (trained on a snapshot taken {metrics['observation_window_days']} "
        f"days before the analysis date, so no future information leaks in). "
        f"The dominant driver is **{top_driver['feature']}**, which "
        f"{top_driver['direction']}.",
        "",
        f"**{money(at_risk_value)}** of projected annual value sits in the High and "
        f"Critical risk bands.",
        "",
        "### Behavioural segments",
        "",
        _table(segments["profile"][[
            "segment_name", "customers", "customer_share_pct", "revenue_share_pct",
            "avg_orders", "avg_lifetime_revenue", "churned_pct",
        ]]),
        "### Churn risk bands",
        "",
        _table(risk_bands),
        "### LTV : CAC by acquisition channel",
        "",
        _table(ratios),
    ])


def section_marketing() -> str:
    models = attribution.attribute()
    economics = attribution.campaign_economics()
    reallocation = attribution.budget_reallocation()

    _write_csv(models, "marketing_attribution")
    _write_csv(economics, "marketing_campaign_economics")

    lines = ["## Marketing", ""]
    if not models.empty:
        undercredited = models.sort_values("upper_funnel_bias", ascending=False).iloc[0]
        lines += [
            f"Last-touch attribution under-credits **{undercredited['channel']}** by "
            f"{money(undercredited['upper_funnel_bias'])} relative to first-touch. "
            f"That gap is the case for funding upper-funnel activity that a "
            f"last-touch budget would starve.",
            "",
            "### Revenue by attribution model",
            "",
            _table(models),
        ]
    profitable = economics[economics["verdict"] == "Profitable"]
    lines += [
        f"**{len(profitable)} of {len(economics)}** campaigns cleared profit "
        f"break-even (profit ROAS above 1.0).",
        "",
        "### Campaign economics",
        "",
        _table(economics[["campaign_name", "channel", "spend", "revenue",
                          "gross_profit", "roas", "profit_roas", "cac", "verdict"]]),
        "### Suggested budget reallocation",
        "",
        _table(reallocation),
        "_Assumes receiving channels hold their current marginal efficiency._",
        "",
    ]
    return "\n".join(lines)


def section_products() -> str:
    lines = datasets.sales_lines()
    products = datasets.products()
    baskets = basket.build_baskets(lines)
    pairs = basket.affinity_pairs(baskets)
    categories = basket.category_affinity(lines)

    _write_csv(products, "product_performance")
    if not pairs.empty:
        _write_csv(pairs, "product_affinity")

    abc = products.groupby("abc_class").agg(
        products=("product_id", "count"),
        revenue=("revenue", "sum"),
    ).round(2).reset_index()
    abc["revenue_share_pct"] = (abc["revenue"] / abc["revenue"].sum() * 100).round(1)

    return "\n".join([
        "## Products",
        "",
        f"**{int(abc.loc[abc['abc_class'] == 'A', 'products'].sum())}** class-A products "
        f"carry {abc.loc[abc['abc_class'] == 'A', 'revenue_share_pct'].sum()}% of revenue.",
        "",
        "### ABC classification",
        "",
        _table(abc),
        "### Top products by revenue",
        "",
        _table(products.nlargest(10, "revenue")[[
            "sku", "product_name", "category", "revenue", "gross_profit",
            "margin_pct", "units_sold", "abc_class", "performance_segment",
        ]]),
        "### Category affinity (lift above 1 means a genuine association)",
        "",
        _table(categories),
        f"### Product pairs ({len(pairs)} clear the support floor)",
        "",
        _table(pairs.head(10) if not pairs.empty else pairs),
    ])


def section_inventory() -> str:
    optimised = optimisation.optimise()
    capital = optimisation.working_capital_opportunity(optimised)
    reorders = optimisation.reorder_list(optimised, top_n=15)

    _write_csv(optimised, "inventory_optimisation")
    _write_csv(reorders, "inventory_reorder_list")

    due = int((optimised["units_to_order"] > 0).sum())
    value = float(optimised["order_value_at_cost"].sum())
    trapped = float(capital["capital_at_cost"].sum())

    return "\n".join([
        "## Inventory",
        "",
        f"**{due}** products are at or below their recommended reorder point, a "
        f"purchase of {money(value)} at cost. Separately, {money(trapped)} of "
        f"working capital sits in overstock and dead stock.",
        "",
        "### ABC x XYZ grid",
        "",
        _table(optimisation.abc_xyz_grid(optimised)),
        "### Working capital opportunity",
        "",
        _table(capital),
        "### Reorder list",
        "",
        _table(reorders),
    ])


def section_forecast() -> str:
    daily = forecast.forecast_daily_revenue(horizon=60, holdout=28)
    monthly = forecast.forecast_monthly_revenue(horizon=6)

    _write_csv(daily["forecast"], "forecast_daily_revenue")
    _write_csv(monthly["forecast"], "forecast_monthly_revenue")

    total = float(monthly["forecast"]["forecast"].sum())
    lower = float(monthly["forecast"]["lower"].sum())
    upper = float(monthly["forecast"]["upper"].sum())

    return "\n".join([
        "## Forecast",
        "",
        f"Next six months: **{money(total)}** "
        f"(80% interval {money(lower)} to {money(upper)}), "
        f"using the **{monthly['model']}** model.",
        "",
        f"The daily model was selected by backtest against a 28-day holdout; "
        f"**{daily['model']}** won.",
        "",
        "### Daily backtest",
        "",
        _table(daily["backtest"]),
        "_`vs_naive_pct` below zero means the model beats a seasonal-naive "
        "baseline. A model that cannot is not worth deploying._",
        "",
        "### Monthly forecast",
        "",
        _table(monthly["forecast"]),
    ])


SECTIONS = {
    "executive": section_executive,
    "sales": section_sales,
    "customers": section_customers,
    "marketing": section_marketing,
    "products": section_products,
    "inventory": section_inventory,
    "forecast": section_forecast,
}


def build_report(only: list[str] | None = None) -> str:
    chosen = only or list(SECTIONS)
    parts = [
        "# PulseAnalytics - analytical insight report",
        "",
        f"Generated {datetime.now():%Y-%m-%d %H:%M}. Every number below is "
        f"reproducible: `python -m analytics.run_analytics`.",
        "",
        "Definitions for every metric are in `docs/kpi-definitions.md`. "
        "Extracts for each section are written to `data/exports/`.",
        "",
    ]
    for name in chosen:
        if name not in SECTIONS:
            log.warning("unknown section %r - skipped", name)
            continue
        log.info("building section: %s", name)
        try:
            parts.append(SECTIONS[name]())
        except Exception as exc:
            log.error("section %s failed: %s", name, exc)
            parts.append(
                f"## {name.title()}\n\n"
                f"> **This section failed to build.**\n>\n"
                f"> `{type(exc).__name__}: {exc}`\n>\n"
                f"> The remaining sections are unaffected.\n"
            )
            log.debug(traceback.format_exc())
        parts.append("")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run every analytical model")
    parser.add_argument("--only", help="comma-separated section names: "
                                       + ", ".join(SECTIONS))
    parser.add_argument("--output", default=str(REPORT_DIR / "insight_report.md"))
    args = parser.parse_args(argv)

    print(banner("PulseAnalytics - analytics run"))
    only = [s.strip() for s in args.only.split(",")] if args.only else None
    report = build_report(only)

    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")

    print(f"\nInsight report -> {path}")
    print(f"CSV extracts    -> {EXPORT_DIR}")
    exported = sorted(EXPORT_DIR.glob("*.csv"))
    for item in exported:
        print(f"  {item.name}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
