"""Operations dashboard - stock health, funnel drop-off, payment success by
gateway, returns and cancellations, pipeline health and data quality.

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
gateways = data.payment_gateway_success()
exceptions = data.order_exceptions()

PERIODS = ["Last 90 days", "All history"]


def outcome_rate(frame: pd.DataFrame, outcome: str) -> float | None:
    """Orders with this outcome per 100 orders placed - a ratio of counts,
    never an average of daily rates."""
    rows = frame[frame["outcome"] == outcome]
    if rows.empty:
        return None
    return float(rows["orders"].sum()) / float(rows["orders_placed"].iloc[0]) * 100


exceptions_90 = exceptions[exceptions["period"] == PERIODS[0]]

tiles = [
    ("Payment failure rate", theme.percent(kpis["payment_failure_rate_pct"]), None,
     f"{theme.compact_money(kpis['payment_amount_at_risk'])} at risk"),
    ("Payment attempts", theme.number(kpis["payment_attempts"]), None, "last 90 days"),
    ("Stocked out", theme.number(kpis["products_stocked_out"]), None,
     f"of {theme.number(kpis['products_tracked'])} products"),
    ("Below reorder", theme.number(kpis["products_below_reorder"]), None,
     "need a purchase order"),
    ("Stock value", theme.compact_money(kpis["stock_value_at_cost"]), None, "at cost"),
    ("Cancellation rate", theme.percent(outcome_rate(exceptions_90, "Cancelled")),
     None, "of orders placed, last 90 days"),
]
for column, (label, value, delta, sub) in zip(st.columns(6), tiles):
    column.markdown(theme.kpi_tile(label, value, delta, sub), unsafe_allow_html=True)
st.write("")

(tab_payments, tab_inventory, tab_funnel, tab_exceptions,
 tab_pipeline, tab_quality) = st.tabs(
    ["Payments", "Stock health", "Conversion funnel",
     "Returns & cancellations", "Pipeline", "Data quality"]
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

    # ---- success by gateway, on both denominators ------------------------ #
    st.subheader("Payment success by gateway")
    gateway_period = st.radio("Period", PERIODS, horizontal=True,
                              key="gateway_period", label_visibility="collapsed")
    by_gateway = gateways[gateways["period"] == gateway_period].copy()

    attempts_total = int(by_gateway["authorisation_attempts"].sum())
    captured_total = int(by_gateway["attempts_captured"].sum())
    orders_total = int(by_gateway["orders_attempted"].sum())
    paid_total = int(by_gateway["orders_paid"].sum())
    retry_total = int(by_gateway["orders_paid_on_retry"].sum())

    def share(numerator: int, denominator: int) -> float | None:
        return numerator / denominator * 100 if denominator else None

    tiles = [
        ("Success per attempt", theme.percent(share(captured_total, attempts_total)),
         None, f"{theme.number(captured_total)} captured ÷ "
               f"{theme.number(attempts_total)} authorisation attempts"),
        ("Success per order", theme.percent(share(paid_total, orders_total)),
         None, f"{theme.number(paid_total)} paid ÷ "
               f"{theme.number(orders_total)} orders attempted"),
        ("Recovered by retry", theme.number(retry_total), None,
         "orders paid after a failed first attempt"),
    ]
    for column, (label, value, delta, sub) in zip(st.columns(3), tiles):
        column.markdown(theme.kpi_tile(label, value, delta, sub), unsafe_allow_html=True)
    st.write("")

    def gateway_chart() -> go.Figure:
        """Two bars per gateway, one per denominator. Same axis, same unit, so
        they are directly comparable - and the gap between them is what retries
        recover."""
        ordered = by_gateway.sort_values("authorisation_attempts", ascending=False)
        figure = go.Figure()
        series = [
            ("attempt_success_rate_pct", "authorisation_attempts",
             "Per attempt (captured ÷ authorisation attempts)", "attempts"),
            ("order_success_rate_pct", "orders_attempted",
             "Per order (orders paid ÷ orders attempted)", "orders"),
        ]
        for index, (rate, denominator, name, unit) in enumerate(series):
            figure.add_trace(go.Bar(
                x=ordered["gateway"], y=ordered[rate], name=name,
                marker=dict(color=theme.series_colour(index)),
                text=[f"{v:.1f}%" for v in ordered[rate]],
                textposition="outside",
                textfont=dict(color=theme.INK_SECONDARY, size=11),
                customdata=ordered[[denominator]],
                hovertemplate="%{x}<br>%{y:.2f}% of %{customdata[0]:,} "
                              + unit + "<extra>" + name + "</extra>",
            ))
        figure.update_traces(marker_cornerradius=4)
        figure.update_layout(barmode="group", bargap=0.3, hovermode="closest")
        figure.update_yaxes(ticksuffix="%", range=[0, 105])
        return theme.apply(figure, f"Payment success by gateway - {gateway_period.lower()}",
                           height=380)

    st.plotly_chart(gateway_chart(), width="stretch")
    st.dataframe(
        by_gateway[["gateway", "authorisation_attempts", "attempts_captured",
                    "attempts_failed", "attempt_success_rate_pct",
                    "orders_attempted", "orders_paid", "orders_paid_on_retry",
                    "order_success_rate_pct"]],
        width="stretch", hide_index=True,
        column_config={
            "gateway": "Gateway",
            "authorisation_attempts": "Authorisation attempts (denominator A)",
            "attempts_captured": "Attempts captured",
            "attempts_failed": "Attempts failed",
            "attempt_success_rate_pct": st.column_config.NumberColumn(
                "Success per attempt % (captured ÷ A)", format="%.2f%%"),
            "orders_attempted": "Orders attempted (denominator B)",
            "orders_paid": "Orders paid",
            "orders_paid_on_retry": "Paid on retry",
            "order_success_rate_pct": st.column_config.NumberColumn(
                "Success per order % (paid ÷ B)", format="%.2f%%"),
        },
    )
    st.markdown(
        theme.note(
            "Two success rates, two denominators, on purpose. <b>Per attempt</b> "
            "divides by every authorisation sent to the gateway, retries "
            "included - it is the number for the gateway conversation. "
            "<b>Per order</b> divides by orders, each counted once against the "
            "gateway of its final attempt - it is what the customer experienced. "
            "Refunds are not authorisation attempts and are in neither. The "
            "source records the payment method only, so the method is the "
            "gateway here."
        ),
        unsafe_allow_html=True,
    )

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

    # Counts come from the inventory mart's own flags - the same definitions
    # the reorder list and the working-capital table use.
    tracked = len(inventory)
    below_reorder = int(inventory["is_below_reorder"].fillna(False).astype(bool).sum())
    status_counts = inventory["stock_status"].value_counts()
    overstocked = int(status_counts.get("Overstocked - markdown", 0))
    dead_stock = int(status_counts.get("Dead stock", 0))
    stocked_out = int(status_counts.get("Stockout - expedite", 0))
    overstock_capital = float(
        capital.loc[capital["bucket"].str.startswith("Overstocked"), "capital_at_cost"].sum()
    )

    tiles = [
        ("Below reorder point", theme.number(below_reorder), None,
         f"{theme.percent(below_reorder / tracked * 100 if tracked else None)} "
         f"of {theme.number(tracked)} products"),
        ("Stocked out", theme.number(stocked_out), None, "expedite"),
        ("Overstocked", theme.number(overstocked), None,
         f"{theme.compact_money(overstock_capital)} excess at cost"),
        ("Dead stock", theme.number(dead_stock), None, "no sales in the window"),
    ]
    for column, (label, value, delta, sub) in zip(st.columns(4), tiles):
        column.markdown(theme.kpi_tile(label, value, delta, sub), unsafe_allow_html=True)
    st.write("")

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
    right.subheader("ABC x XYZ distribution")
    right.caption("Revenue class against demand predictability. ABC says what "
                  "matters; XYZ says how hard it is to plan.")

    def abc_xyz_heatmap() -> go.Figure:
        abc_levels, xyz_levels = ["A", "B", "C"], ["X", "Y", "Z"]
        counts = (optimised["abc_xyz"].value_counts()
                  .reindex([a + x for a in abc_levels for x in xyz_levels], fill_value=0))
        grid = [[int(counts[a + x]) for x in xyz_levels] for a in abc_levels]
        total = max(int(counts.sum()), 1)
        ramp = theme.SEQUENTIAL_BLUE
        figure = go.Figure(go.Heatmap(
            z=grid, x=["X - steady", "Y - variable", "Z - erratic"],
            y=["A - top revenue", "B - middle", "C - long tail"],
            colorscale=[[i / (len(ramp) - 1), c] for i, c in enumerate(ramp)],
            showscale=False, xgap=2, ygap=2,
            text=[[f"{v} ({v / total * 100:.0f}%)" for v in row] for row in grid],
            texttemplate="%{text}", textfont=dict(size=13),
            hovertemplate="%{y} / %{x}<br>%{z} products<extra></extra>",
        ))
        figure.update_yaxes(autorange="reversed", showgrid=False)
        figure.update_xaxes(showgrid=False, side="top")
        return theme.apply(figure, "", height=300, legend=False)

    right.plotly_chart(abc_xyz_heatmap(), width="stretch")

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

    stages = funnel.copy()
    stages["transition"] = (stages["step_name"].shift(1).fillna("")
                            + " → " + stages["step_name"])
    stages["drop_off_pct"] = (100 - stages["step_conversion_pct"]).round(2)
    transitions = stages.iloc[1:]

    def drop_off_chart() -> go.Figure:
        """Where sessions leave. The worst transition is the one to work on,
        so it is the only bar in the alert hue - the rest stay neutral."""
        worst = transitions["drop_off_pct"].idxmax() if not transitions.empty else None
        figure = go.Figure(go.Bar(
            x=transitions["drop_off_pct"], y=transitions["transition"],
            orientation="h",
            marker=dict(color=[theme.STATUS["serious"] if i == worst
                               else theme.series_colour(0)
                               for i in transitions.index]),
            text=[f"{d:.1f}%  ({n:,} sessions)" for d, n in
                  zip(transitions["drop_off_pct"], transitions["dropped_sessions"])],
            textposition="outside", textfont=dict(color=theme.INK_SECONDARY, size=12),
            hovertemplate="%{y}<br>%{x:.1f}% of sessions dropped<extra></extra>",
        ))
        figure.update_traces(marker_cornerradius=4)
        figure.update_layout(hovermode="closest")
        figure.update_yaxes(autorange="reversed")
        figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE, showline=False,
                            ticksuffix="%", range=[0, 110])
        return theme.apply(figure, "Drop-off between stages", height=420, legend=False)

    left, right = st.columns(2)
    left.plotly_chart(funnel_chart(), width="stretch")
    right.plotly_chart(drop_off_chart(), width="stretch")

    st.dataframe(
        stages[["step_number", "step_name", "sessions", "pct_of_top",
                "step_conversion_pct", "drop_off_pct", "dropped_sessions"]],
        width="stretch", hide_index=True,
        column_config={
            "step_number": "#",
            "step_name": "Stage",
            "sessions": "Sessions reaching stage",
            "pct_of_top": st.column_config.NumberColumn(
                "% of top of funnel", format="%.1f%%"),
            "step_conversion_pct": st.column_config.NumberColumn(
                "Conversion from previous stage", format="%.1f%%"),
            "drop_off_pct": st.column_config.NumberColumn(
                "Drop-off from previous stage", format="%.1f%%"),
            "dropped_sessions": "Sessions dropped",
        },
    )

    st.subheader("By device")
    st.dataframe(data.funnel_by_device(), width="stretch", hide_index=True)

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
with tab_exceptions:
    exceptions_period = st.radio("Period", PERIODS, horizontal=True,
                                 key="exceptions_period", label_visibility="collapsed")
    scoped = exceptions[exceptions["period"] == exceptions_period]

    if scoped.empty:
        st.info("No cancelled or returned orders in this period.")
    else:
        placed = int(scoped["orders_placed"].iloc[0])
        cancelled = scoped[scoped["outcome"] == "Cancelled"]
        returned = scoped[scoped["outcome"] == "Returned"]
        unrecorded = scoped[~scoped["is_mapped"].astype(bool)]
        exception_orders = int(scoped["orders"].sum())

        tiles = [
            ("Cancellation rate", theme.percent(outcome_rate(scoped, "Cancelled")), None,
             f"{theme.number(cancelled['orders'].sum())} of "
             f"{theme.number(placed)} orders placed"),
            ("Return rate", theme.percent(outcome_rate(scoped, "Returned")), None,
             f"{theme.number(returned['orders'].sum())} of "
             f"{theme.number(placed)} orders placed"),
            ("Value cancelled", theme.compact_money(cancelled["order_value"].sum()),
             None, "order value never collected"),
            ("Value returned", theme.compact_money(returned["order_value"].sum()),
             None, "order value refunded"),
            ("No usable reason", theme.number(unrecorded["orders"].sum()), None,
             f"{theme.percent(unrecorded['orders'].sum() / exception_orders * 100)} "
             f"of exceptions - not recorded or unmapped"),
        ]
        for column, (label, value, delta, sub) in zip(st.columns(5), tiles):
            column.markdown(theme.kpi_tile(label, value, delta, sub),
                            unsafe_allow_html=True)
        st.write("")

        # Colour follows the reason GROUP, in a fixed order, so 'Fulfilment'
        # is the same hue on both charts. The two gap buckets are neutral grey
        # so they read as missing data rather than as a cause.
        GROUP_ORDER = ["Product", "Fulfilment", "Customer", "Payment", "Inventory"]
        GAP_GROUPS = ["Not recorded", "Unmapped"]

        def group_colour(group: str) -> str:
            if group in GAP_GROUPS:
                return theme.INK_MUTED
            return theme.series_colour(GROUP_ORDER.index(group)
                                       if group in GROUP_ORDER else len(GROUP_ORDER))

        def reason_chart(rows: pd.DataFrame, outcome: str) -> go.Figure:
            rows = rows.sort_values("orders", ascending=True)
            figure = go.Figure()
            for group in GROUP_ORDER + GAP_GROUPS + sorted(
                    set(rows["reason_group"]) - set(GROUP_ORDER) - set(GAP_GROUPS)):
                subset = rows[rows["reason_group"] == group]
                if subset.empty:
                    continue
                figure.add_trace(go.Bar(
                    x=subset["orders"], y=subset["reason_label"], orientation="h",
                    name=group, marker=dict(color=group_colour(group)),
                    text=[f"{n:,}  ({s:.0f}%)" for n, s in
                          zip(subset["orders"], subset["share_of_outcome_pct"])],
                    textposition="outside",
                    textfont=dict(color=theme.INK_SECONDARY, size=12),
                    customdata=subset[["rate_of_orders_placed_pct", "order_value"]],
                    hovertemplate="%{y}<br>%{x:,} orders"
                                  "<br>%{customdata[0]:.2f} per 100 orders placed"
                                  "<br>%{customdata[1]:$,.0f} order value"
                                  "<extra>" + group + "</extra>",
                ))
            figure.update_traces(marker_cornerradius=4)
            figure.update_layout(hovermode="closest", barmode="overlay")
            figure.update_yaxes(categoryorder="array",
                                categoryarray=list(rows["reason_label"]))
            figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE, showline=False)
            return theme.apply(figure, f"{outcome} orders by reason", height=380)

        left, right = st.columns(2)
        if not cancelled.empty:
            left.plotly_chart(reason_chart(cancelled, "Cancelled"), width="stretch")
        if not returned.empty:
            right.plotly_chart(reason_chart(returned, "Returned"), width="stretch")

        def monthly_rates_chart() -> go.Figure:
            monthly = data.order_exceptions_monthly()
            figure = go.Figure()
            for index, (column, name) in enumerate([
                ("cancellation_rate_pct", "Cancellation rate"),
                ("return_rate_pct", "Return rate"),
            ]):
                figure.add_trace(go.Scatter(
                    x=monthly["month_start"], y=monthly[column], name=name,
                    mode="lines+markers",
                    line=dict(color=theme.series_colour(index), width=2),
                    marker=dict(size=5),
                    customdata=monthly[["orders_placed"]],
                    hovertemplate="%{x|%b %Y}<br>%{y:.2f}% of %{customdata[0]:,} "
                                  "orders placed<extra>" + name + "</extra>",
                ))
            figure.update_yaxes(ticksuffix="%", rangemode="tozero")
            return theme.apply(figure, "Cancellation and return rate by month",
                               height=320)

        st.plotly_chart(monthly_rates_chart(), width="stretch")

        st.subheader("By reason")
        st.dataframe(
            scoped[["outcome", "reason_group", "reason_label", "reason_code",
                    "orders", "outcome_orders", "share_of_outcome_pct",
                    "orders_placed", "rate_of_orders_placed_pct", "order_value"]],
            width="stretch", hide_index=True,
            column_config={
                "outcome": "Outcome",
                "reason_group": "Group",
                "reason_label": "Reason",
                "reason_code": "Source code",
                "orders": "Orders",
                "outcome_orders": "All orders with this outcome (denominator A)",
                "share_of_outcome_pct": st.column_config.NumberColumn(
                    "Share of outcome % (orders ÷ A)", format="%.1f%%"),
                "orders_placed": "Orders placed (denominator B)",
                "rate_of_orders_placed_pct": st.column_config.NumberColumn(
                    "Per 100 orders placed (orders ÷ B)", format="%.2f"),
                "order_value": st.column_config.NumberColumn(
                    "Order value", format="dollar"),
            },
        )
        st.markdown(
            theme.note(
                "<b>Share of outcome</b> says what to fix first: of all returns, "
                "how many were for this reason. <b>Per 100 orders placed</b> is "
                "the number that moves when a fix works, and the one to compare "
                "across periods. A reason left blank in the order system is "
                "shown as <b>Not recorded</b>, a code with no mapping as "
                "<b>Unmapped</b> - both stay in the totals rather than "
                "disappearing from them."
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
