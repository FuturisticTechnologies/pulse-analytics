"""PulseAnalytics - Executive dashboard (the app's home page).

    streamlit run dashboards/streamlit/app.py

Five pages, each written for one audience:

    Executive     is the business healthy, and what changed
    Sales         what sold, where, and why the number moved
    Customers     who they are, what they are worth, who is leaving
    Marketing     what the spend bought
    Operations    payments, inventory, pipeline and data quality
    Real-time     what is happening right now

This page answers only the first question. Everything on it is a trailing-90-day
figure against the preceding 90 days, because a single number with no comparison
is not information.
"""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboards.streamlit import data_access as data   # noqa: E402
from dashboards.streamlit import theme                 # noqa: E402

st.set_page_config(page_title="PulseAnalytics - Executive", page_icon="◑",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(theme.KPI_CSS, unsafe_allow_html=True)


def sidebar() -> None:
    status = data.warehouse_status()
    with st.sidebar:
        st.markdown("### PulseAnalytics")
        st.caption("Real-time business analytics platform")
        st.divider()
        st.markdown(f"**Engine** `{status['engine']}`")
        st.markdown(f"**Warehouse** {'ready' if status['ready'] else 'not built'}")
        st.markdown(f"**Stream** {'live data' if status['stream_ready'] else 'no events'}")
        st.divider()
        if st.button("Refresh data", width="stretch"):
            st.cache_data.clear()
            st.rerun()
        st.caption(
            "Every metric here is defined once, in SQL, and documented in "
            "`docs/kpi-definitions.md`. No page computes its own version."
        )


def kpi_row(kpis) -> None:
    tiles = [
        ("Revenue (90d)", theme.compact_money(kpis["revenue_90d"]),
         theme.delta_text(kpis["revenue_change_pct"]),
         f"vs {theme.compact_money(kpis['revenue_prev_90d'])} prior period"),
        ("Gross profit", theme.compact_money(kpis["gross_profit_90d"]),
         None, f"{theme.percent(kpis['gross_margin_pct'])} margin"),
        ("Orders", theme.number(kpis["orders_90d"]),
         theme.delta_text(kpis["orders_change_pct"]),
         f"AOV {theme.money(kpis['avg_order_value'])}"),
        ("Active customers", theme.number(kpis["active_customers_90d"]),
         theme.delta_text(kpis["new_customers_change_pct"]),
         f"{theme.number(kpis['new_customers_90d'])} newly acquired"),
        ("Repeat rate", theme.percent(kpis["repeat_rate_pct"]),
         None, f"{theme.number(kpis['at_risk_customers'])} customers at risk"),
        ("Blended ROAS", f"{kpis['blended_roas']:.2f}x",
         None, f"CAC {theme.money(kpis['blended_cac'])}"),
    ]
    for column, (label, value, delta, sub) in zip(st.columns(6), tiles):
        column.markdown(theme.kpi_tile(label, value, delta, sub), unsafe_allow_html=True)


def revenue_trend() -> go.Figure:
    """Daily revenue with its 7-day moving average.

    Two series on ONE axis - both are revenue in dollars, so they are directly
    comparable. The raw line is deliberately the quieter of the two: the moving
    average is the number an operator should react to, and daily noise is
    context, not signal.
    """
    daily = data.daily_sales().tail(180)
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=daily["order_date"], y=daily["revenue"], name="Daily revenue",
        mode="lines", line=dict(color=theme.series_colour(0), width=1.2),
        opacity=0.45, hovertemplate="%{y:$,.0f}<extra>Daily</extra>",
    ))
    figure.add_trace(go.Scatter(
        x=daily["order_date"], y=daily["revenue_ma7"], name="7-day average",
        mode="lines", line=dict(color=theme.series_colour(0), width=2),
        hovertemplate="%{y:$,.0f}<extra>7-day average</extra>",
    ))
    # Direct-label the endpoint only - a number on every point goes unread.
    last = daily.iloc[-1]
    figure.add_annotation(
        x=last["order_date"], y=last["revenue_ma7"],
        text=theme.compact_money(last["revenue_ma7"]),
        showarrow=False, xanchor="left", xshift=8,
        font=dict(color=theme.INK_PRIMARY, size=12),
    )
    return theme.apply(figure, "Revenue - last 180 days", height=320, y_prefix="$")


def monthly_bars() -> go.Figure:
    """Monthly revenue. One series, one colour - length already encodes size,
    so a value ramp would burn the colour channel on nothing."""
    monthly = data.monthly_sales()
    figure = go.Figure(go.Bar(
        x=monthly["month_start"], y=monthly["revenue"],
        marker=dict(color=theme.series_colour(0),
                    line=dict(width=0)),
        name="Revenue",
        hovertemplate="%{x|%b %Y}<br>%{y:$,.0f}<extra></extra>",
    ))
    figure.update_traces(marker_cornerradius=4)
    return theme.apply(figure, "Monthly revenue", height=320,
                       legend=False, y_prefix="$")


def region_bars() -> go.Figure:
    frame = data.regions().sort_values("revenue")
    figure = go.Figure(go.Bar(
        x=frame["revenue"], y=frame["region_name"], orientation="h",
        marker=dict(color=theme.series_colour(0)),
        text=[theme.compact_money(v) for v in frame["revenue"]],
        textposition="outside",
        textfont=dict(color=theme.INK_SECONDARY, size=12),
        hovertemplate="%{y}<br>%{x:$,.0f}<extra></extra>",
    ))
    figure.update_traces(marker_cornerradius=4)
    figure.update_layout(hovermode="closest")
    figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE, showline=False)
    return theme.apply(figure, "Revenue by region", height=320, legend=False)


def category_bars() -> go.Figure:
    frame = theme.fold_tail(data.categories(), "category", "revenue", keep=7)
    frame = frame.sort_values("revenue")
    figure = go.Figure(go.Bar(
        x=frame["revenue"], y=frame["category"], orientation="h",
        marker=dict(color=theme.series_colour(2)),
        text=[theme.compact_money(v) for v in frame["revenue"]],
        textposition="outside",
        textfont=dict(color=theme.INK_SECONDARY, size=12),
        hovertemplate="%{y}<br>%{x:$,.0f}<extra></extra>",
    ))
    figure.update_traces(marker_cornerradius=4)
    figure.update_layout(hovermode="closest")
    figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE, showline=False)
    return theme.apply(figure, "Revenue by category", height=320, legend=False)


def main() -> None:
    sidebar()
    st.title("Executive dashboard")

    if not data.require_warehouse():
        return

    kpis = data.executive_kpis()
    st.caption(
        f"Trailing 90 days to {kpis['as_of_date']:%d %b %Y}, "
        f"compared with the 90 days before it."
    )
    kpi_row(kpis)
    st.write("")

    left, right = st.columns([3, 2])
    left.plotly_chart(revenue_trend(), width="stretch")
    right.plotly_chart(monthly_bars(), width="stretch")

    left, right = st.columns(2)
    left.plotly_chart(region_bars(), width="stretch")
    right.plotly_chart(category_bars(), width="stretch")

    st.subheader("What to look at")
    monthly = data.monthly_sales()
    regions = data.regions()
    inventory = data.inventory()

    findings = []
    if len(monthly) >= 2 and monthly["revenue_mom_pct"].iloc[-1] is not None:
        latest = monthly.iloc[-1]
        findings.append(
            f"**{latest['month_start']:%B %Y}** closed at "
            f"{theme.compact_money(latest['revenue'])}, "
            f"{theme.percent(latest['revenue_mom_pct'])} month over month."
        )
    declining = regions[regions["revenue_trend_pct"].fillna(0) < 0]
    if not declining.empty:
        worst = declining.sort_values("revenue_trend_pct").iloc[0]
        findings.append(
            f"**{worst['region_name']}** is down "
            f"{theme.percent(abs(worst['revenue_trend_pct']))} over the last 90 days "
            f"against the 90 before."
        )
    urgent = inventory[inventory["action_priority"] <= 2]
    if not urgent.empty:
        findings.append(
            f"**{len(urgent)} products** need a purchase order - "
            f"{int((inventory['is_stockout']).sum())} are already stocked out."
        )
    findings.append(
        f"**{theme.percent(kpis['payment_failure_rate_pct'])}** of payment attempts "
        f"failed, holding {theme.compact_money(kpis['payment_amount_at_risk'])} "
        f"of revenue."
    )
    for finding in findings:
        st.markdown(f"- {finding}")

    st.markdown(
        theme.note(
            "Attribution is last-touch, which is the limit of what the source "
            "system records. The Marketing page shows how the picture changes "
            "under first-touch, linear, time-decay and position-based models."
        ),
        unsafe_allow_html=True,
    )


main()
