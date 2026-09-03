"""Operations dashboard - payments, inventory, pipeline health and data quality.

The page an on-call analyst opens. Everything on it is something that can be
acted on today.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from analytics.inventory import optimisation             # noqa: E402
from dashboards.streamlit import data_access as data     # noqa: E402
from dashboards.streamlit import theme                   # noqa: E402

st.set_page_config(page_title="PulseAnalytics - Operations", page_icon="◑", layout="wide")
st.markdown(theme.KPI_CSS, unsafe_allow_html=True)

st.title("Operations")
if not data.require_warehouse():
    st.stop()

kpis = data.executive_kpis()
inventory = data.inventory()
payments = data.payment_health()

tiles = [
    ("Payment failure rate", theme.percent(kpis["payment_failure_rate_pct"]), None,
     f"{theme.compact_money(kpis['payment_amount_at_risk'])} at risk"),
    ("Payment attempts", theme.number(kpis["payment_attempts"]), None, "last 90 days"),
    ("Stocked out", theme.number(kpis["products_stocked_out"]), None,
     f"of {theme.number(kpis['products_tracked'])} products"),
    ("Below reorder", theme.number(kpis["products_below_reorder"]), None,
     "need a purchase order"),
    ("Stock value", theme.compact_money(kpis["stock_value_at_cost"]), None, "at cost"),
    ("Cancellation rate", theme.percent(
        data.daily_sales().tail(90)["cancellation_rate_pct"].mean()), None,
     "90-day average"),
]
for column, (label, value, delta, sub) in zip(st.columns(6), tiles):
    column.markdown(theme.kpi_tile(label, value, delta, sub), unsafe_allow_html=True)
st.write("")

tab_payments, tab_inventory, tab_funnel, tab_pipeline, tab_quality = st.tabs(
    ["Payments", "Inventory", "Conversion funnel", "Pipeline", "Data quality"]
)

# --------------------------------------------------------------------------- #
with tab_payments:
    def failure_trend() -> go.Figure:
        daily = (payments.groupby("payment_date")
                 .agg(attempts=("attempts", "sum"), failed=("failed", "sum"))
                 .reset_index())
        daily["failure_rate_pct"] = (
            daily["failed"] / daily["attempts"].replace(0, pd.NA) * 100
        ).round(2)
        daily["rate_ma7"] = daily["failure_rate_pct"].rolling(7, min_periods=1).mean()

        figure = go.Figure()
        figure.add_trace(go.Scatter(
            x=daily["payment_date"], y=daily["failure_rate_pct"],
            name="Daily failure rate", mode="lines",
            line=dict(color=theme.STATUS["critical"], width=1.2), opacity=0.4,
            hovertemplate="%{y:.2f}%<extra>Daily</extra>",
        ))
        figure.add_trace(go.Scatter(
            x=daily["payment_date"], y=daily["rate_ma7"], name="7-day average",
            mode="lines", line=dict(color=theme.STATUS["critical"], width=2),
            hovertemplate="%{y:.2f}%<extra>7-day average</extra>",
        ))
        figure.update_yaxes(ticksuffix="%")
        return theme.apply(figure, "Payment failure rate", height=340)

    def method_chart() -> go.Figure:
        by_method = (payments.groupby("payment_method")
                     .agg(attempts=("attempts", "sum"), failed=("failed", "sum"))
                     .reset_index())
        by_method["failure_rate_pct"] = (
            by_method["failed"] / by_method["attempts"].replace(0, pd.NA) * 100
        ).round(2)
        by_method = by_method.sort_values("failure_rate_pct")
        figure = go.Figure(go.Bar(
            x=by_method["failure_rate_pct"], y=by_method["payment_method"],
            orientation="h", marker=dict(color=theme.series_colour(0)),
            text=[f"{v:.1f}%" for v in by_method["failure_rate_pct"]],
            textposition="outside", textfont=dict(color=theme.INK_SECONDARY, size=12),
            customdata=by_method[["attempts"]],
            hovertemplate="%{y}<br>%{x:.2f}%% of %{customdata[0]:,} attempts<extra></extra>",
        ))
        figure.update_traces(marker_cornerradius=4)
        figure.update_layout(hovermode="closest")
        figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE,
                            showline=False, ticksuffix="%")
        return theme.apply(figure, "Failure rate by payment method",
                           height=340, legend=False)

    left, right = st.columns(2)
    left.plotly_chart(failure_trend(), width="stretch")
    right.plotly_chart(method_chart(), width="stretch")

    st.subheader("Why payments fail")
    failures = data.payment_failures()
    st.dataframe(
        failures[["failure_reason", "failure_category", "payment_method", "failures",
                  "recovered", "lost", "recovery_rate_pct", "amount_at_risk",
                  "share_of_failures_pct"]],
        width="stretch", hide_index=True,
    )
    st.markdown(
        theme.note(
            "<b>Recovered</b> means a later attempt on the same order was "
            "captured. A high recovery rate on an issuer decline means the retry "
            "logic is working; a low one on a technical failure means it is not. "
            "Two success rates are published deliberately - "
            "<code>attempt_failure_rate_pct</code> measures the gateway, "
            "<code>order_success_rate_pct</code> measures the customer experience."
        ),
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------- #
with tab_inventory:
    with st.spinner("Optimising stock policy..."):
        optimised = optimisation.optimise()
        capital = optimisation.working_capital_opportunity(optimised)
        reorders = optimisation.reorder_list(optimised, top_n=50)

    def status_chart() -> go.Figure:
        counts = (optimised.groupby("stock_status")["product_id"]
                  .count().reset_index(name="products")
                  .sort_values("products"))
        # Status is a state, not an identity: reserved status hues, each paired
        # with its written label on the axis so colour never carries it alone.
        status_colours = {
            "Stockout - expedite": theme.STATUS["critical"],
            "Reorder now": theme.STATUS["serious"],
            "Low cover": theme.STATUS["warning"],
            "Overstocked - markdown": theme.series_colour(6),
            "Dead stock": theme.INK_MUTED,
            "Healthy": theme.STATUS["good"],
        }
        figure = go.Figure(go.Bar(
            x=counts["products"], y=counts["stock_status"], orientation="h",
            marker=dict(color=[status_colours.get(s, theme.INK_MUTED)
                               for s in counts["stock_status"]]),
            text=counts["products"], textposition="outside",
            textfont=dict(color=theme.INK_SECONDARY, size=12),
            hovertemplate="%{y}<br>%{x} products<extra></extra>",
        ))
        figure.update_traces(marker_cornerradius=4)
        figure.update_layout(hovermode="closest")
        figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE, showline=False)
        return theme.apply(figure, "Products by stock status", height=340,
                           legend=False)

    def stock_value_trend() -> go.Figure:
        weekly = (data.inventory_weekly().groupby("snapshot_date")
                  .agg(stock_value_at_cost=("stock_value_at_cost", "sum"))
                  .reset_index())
        figure = go.Figure(go.Scatter(
            x=weekly["snapshot_date"], y=weekly["stock_value_at_cost"],
            mode="lines", name="Stock at cost",
            line=dict(color=theme.series_colour(0), width=2),
            fill="tozeroy", fillcolor="rgba(42,120,214,0.10)",
            hovertemplate="%{x|%d %b %Y}<br>%{y:$,.0f}<extra></extra>",
        ))
        return theme.apply(figure, "Stock value at cost, weekly", height=340,
                           legend=False, y_prefix="$")

    left, right = st.columns(2)
    left.plotly_chart(status_chart(), width="stretch")
    right.plotly_chart(stock_value_trend(), width="stretch")

    st.markdown(
        theme.note(
            "Stock balances are <b>semi-additive</b>: they sum across products "
            "but not across dates. Every figure here reads the latest snapshot "
            "per product, never a SUM over time - which would report stock the "
            "business never had."
        ),
        unsafe_allow_html=True,
    )

    left, right = st.columns([2, 3])
    left.subheader("Working capital")
    left.dataframe(capital, width="stretch", hide_index=True)
    right.subheader("ABC x XYZ")
    right.caption("Revenue class against demand predictability. ABC says what "
                  "matters; XYZ says how hard it is to plan.")
    right.dataframe(optimisation.abc_xyz_grid(optimised),
                    width="stretch", hide_index=True)

    st.subheader(f"Reorder list - {int((optimised['units_to_order'] > 0).sum())} "
                 f"products due, {theme.money(optimised['order_value_at_cost'].sum())} "
                 f"at cost")
    st.dataframe(reorders, width="stretch", hide_index=True)

# --------------------------------------------------------------------------- #
with tab_funnel:
    funnel = data.funnel()

    def funnel_chart() -> go.Figure:
        """Ordinal ramp: the stages have a natural order, so a light-to-dark
        single hue is the right encoding - and it starts dark enough to stay
        readable against the surface."""
        ramp = theme.ORDINAL_BLUE
        colours = [ramp[int(i * (len(ramp) - 1) / max(len(funnel) - 1, 1))]
                   for i in range(len(funnel))]
        figure = go.Figure(go.Bar(
            x=funnel["sessions"], y=funnel["step_name"], orientation="h",
            marker=dict(color=colours),
            text=[f"{s:,} ({p:.0f}%)" for s, p in
                  zip(funnel["sessions"], funnel["pct_of_top"])],
            textposition="outside", textfont=dict(color=theme.INK_SECONDARY, size=12),
            customdata=funnel[["step_conversion_pct", "dropped_sessions"]],
            hovertemplate="%{y}<br>%{x:,} sessions"
                          "<br>%{customdata[0]:.1f}% of the previous step"
                          "<br>%{customdata[1]:,} dropped<extra></extra>",
        ))
        figure.update_traces(marker_cornerradius=4)
        figure.update_layout(hovermode="closest")
        figure.update_yaxes(autorange="reversed")
        figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE, showline=False)
        return theme.apply(figure, "Session funnel", height=420, legend=False)

    left, right = st.columns([3, 2])
    left.plotly_chart(funnel_chart(), width="stretch")
    right.dataframe(data.funnel_by_device(), width="stretch", hide_index=True,
                    height=420)

    st.markdown(
        theme.note(
            "Counted on <b>sessions</b>, not events. A visitor who views ten "
            "products in one visit is one session that reached product-view, not "
            "ten. Steps are 'reached at least this stage', so the funnel is "
            "monotonically decreasing by construction and cannot show the "
            "impossible above-100% step conversion that event-counted funnels do."
        ),
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------- #
with tab_pipeline:
    runs = data.pipeline_runs(60)
    if runs.empty:
        st.info("No pipeline runs recorded yet.")
    else:
        latest_run = runs.iloc[0]["run_id"]
        current = runs[runs["run_id"] == latest_run]
        failed = int((current["status"] == "failed").sum())

        left, right = st.columns([1, 3])
        left.markdown(theme.kpi_tile(
            "Last run", "Failed" if failed else "Success",
            (f"{failed} stage(s) failed", theme.NEGATIVE_TEXT) if failed
            else ("all stages green", theme.POSITIVE_TEXT),
            f"{current['duration_sec'].sum():.1f}s total",
        ), unsafe_allow_html=True)

        figure = go.Figure(go.Bar(
            x=current["duration_sec"], y=current["stage"], orientation="h",
            marker=dict(color=[theme.STATUS["critical"] if s == "failed"
                               else theme.series_colour(0)
                               for s in current["status"]]),
            text=[f"{v:.2f}s" for v in current["duration_sec"]],
            textposition="outside", textfont=dict(color=theme.INK_SECONDARY, size=12),
            customdata=current[["rows_out"]],
            hovertemplate="%{y}<br>%{x:.2f}s<br>%{customdata[0]:,} rows<extra></extra>",
        ))
        figure.update_traces(marker_cornerradius=4)
        figure.update_layout(hovermode="closest")
        figure.update_yaxes(autorange="reversed")
        figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE, showline=False)
        right.plotly_chart(
            theme.apply(figure, f"Stage durations - run {latest_run}",
                        height=300, legend=False),
            width="stretch",
        )

        st.subheader("Run history")
        st.dataframe(
            runs[["run_id", "stage", "status", "started_at", "duration_sec",
                  "rows_out", "message"]],
            width="stretch", hide_index=True,
        )

# --------------------------------------------------------------------------- #
with tab_quality:
    summary = data.quality_summary()
    results = data.quality_results()

    if summary.empty:
        st.info("No data-quality run recorded yet. Run "
                "`python -m etl.pipeline --quality-only`.")
    else:
        latest = summary.iloc[0]
        tiles = [
            ("Pass rate", theme.percent(latest["pass_rate_pct"]), None,
             f"{int(latest['checks_run'])} checks"),
            ("Errors", theme.number(latest["errors"]),
             ("blocking" if latest["errors"] else "none", theme.NEGATIVE_TEXT
              if latest["errors"] else theme.POSITIVE_TEXT), ""),
            ("Warnings", theme.number(latest["warnings"]), None,
             "known, quantified, accepted"),
            ("Checked at", f"{pd.to_datetime(latest['checked_at']):%H:%M}", None,
             f"{pd.to_datetime(latest['checked_at']):%d %b %Y}"),
        ]
        for column, (label, value, delta, sub) in zip(st.columns(4), tiles):
            column.markdown(theme.kpi_tile(label, value, delta, sub),
                            unsafe_allow_html=True)
        st.write("")

        by_dimension = (results.groupby(["dimension", "status"])
                        .size().reset_index(name="checks"))
        figure = go.Figure()
        for index, (status, label, colour) in enumerate([
            ("pass", "Passed", theme.STATUS["good"]),
            ("fail", "Failed", theme.STATUS["critical"]),
        ]):
            subset = by_dimension[by_dimension["status"] == status]
            figure.add_trace(go.Bar(
                x=subset["dimension"], y=subset["checks"], name=label,
                marker=dict(color=colour),
                hovertemplate="%{x}<br>%{y} " + label.lower() + "<extra></extra>",
            ))
        figure.update_traces(marker_cornerradius=4)
        # 2px surface gap between stacked segments, never a stroke.
        figure.update_layout(barmode="stack", bargap=0.35)
        st.plotly_chart(
            theme.apply(figure, "Checks by quality dimension", height=320),
            width="stretch",
        )

        failing = results[results["status"] == "fail"]
        if failing.empty:
            st.success("Every check passed on the latest run.")
        else:
            st.subheader("Failing checks")
            st.dataframe(
                failing[["severity", "layer", "table_name", "check_name",
                         "dimension", "failed_rows", "total_rows",
                         "observed_value", "threshold_value", "details"]],
                width="stretch", hide_index=True,
            )

        st.subheader("All checks")
        st.dataframe(
            results[["status", "severity", "dimension", "layer", "table_name",
                     "check_name", "observed_value", "threshold_value"]],
            width="stretch", hide_index=True,
        )
        st.markdown(
            theme.note(
                "Non-zero thresholds are deliberate. Where the source system is "
                "known to be imperfect - a fraction of a percent of customers "
                "have no email - the tolerance encodes an accepted business "
                "reality. Setting it to zero would turn a known issue into a "
                "nightly false alarm, and a suite that cries wolf gets switched "
                "off."
            ),
            unsafe_allow_html=True,
        )
