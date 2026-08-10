"""Real-time dashboard - what is happening right now.

Reads ``ops.stream_events``, which the consumer writes continuously. Windows are
measured in **event time** (the newest event in the stream), not wall-clock time,
so a replayed stream lights this page up exactly as the live one did.

To see it move:

    python -m streaming.producer.event_producer --rate 8 --duration 0
    python -m streaming.consumer.stream_consumer --duration 0
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dashboards.streamlit import data_access as data     # noqa: E402
from dashboards.streamlit import theme                   # noqa: E402
from pulse.config import STREAM                          # noqa: E402
from streaming.processors.kpi_processor import RealtimeKpiProcessor  # noqa: E402

st.set_page_config(page_title="PulseAnalytics - Real-time", page_icon="◑", layout="wide")
st.markdown(theme.KPI_CSS, unsafe_allow_html=True)

st.title("Real-time")

controls = st.columns([2, 2, 2, 4])
window_minutes = controls[0].selectbox("Window", [15, 30, 60, 120, 240], index=2,
                                       format_func=lambda m: f"Last {m} minutes")
auto_refresh = controls[1].toggle("Auto refresh", value=False)
refresh_seconds = controls[2].select_slider("Every", options=[2, 5, 10, 30], value=5)

status = data.warehouse_status()
if not status.get("stream_ready"):
    st.warning("No events have been landed yet.")
    st.code(
        "# terminal 1 - write 45 minutes of history, then stream live\n"
        "python -m streaming.producer.event_producer --backfill-minutes 45\n"
        "python -m streaming.producer.event_producer --rate 8 --duration 0\n\n"
        "# terminal 2 - land them in the warehouse\n"
        "python -m streaming.consumer.stream_consumer --duration 0",
        language="bash",
    )
    st.caption(f"Event bus backend: `{STREAM.backend}`")
    st.stop()

processor = RealtimeKpiProcessor(window_minutes=window_minutes)
snapshot = processor.compute()

if snapshot is None:
    st.info("The stream is empty for this window. Widen it, or start the producer.")
    st.stop()

# --------------------------------------------------------------------------- #
# Live tiles
# --------------------------------------------------------------------------- #
failure_rate = float(snapshot["failure_rate_pct"])
tiles = [
    ("Orders", theme.number(snapshot["orders"]), None,
     f"last {window_minutes} minutes of stream time"),
    ("Revenue", theme.compact_money(snapshot["revenue"]), None,
     f"AOV {theme.money(snapshot['avg_order_value'])}"),
    ("Buying customers", theme.number(snapshot["buying_customers"]), None,
     f"{theme.number(snapshot['active_sessions'])} active sessions"),
    ("Payment failures", theme.number(snapshot["payment_failures"]),
     # Status is carried by the word as well as the colour.
     (f"{failure_rate:.1f}% of attempts",
      theme.NEGATIVE_TEXT if failure_rate > 10 else theme.INK_SECONDARY),
     f"{theme.compact_money(snapshot['amount_at_risk'])} at risk"),
    ("Stockout alerts", theme.number(snapshot["stockout_alerts"]), None,
     f"{theme.number(snapshot['low_stock_alerts'])} low stock"),
    ("Stream position", f"{pd.to_datetime(snapshot['window_end']):%H:%M:%S}", None,
     f"backend `{STREAM.backend}`"),
]
for column, (label, value, delta, sub) in zip(st.columns(6), tiles):
    column.markdown(theme.kpi_tile(label, value, delta, sub), unsafe_allow_html=True)
st.write("")


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def orders_per_minute() -> go.Figure:
    frame = data.realtime_minutes(window_minutes)
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=frame["minute_bucket"], y=frame["revenue"], name="Revenue per minute",
        mode="lines", line=dict(color=theme.series_colour(0), width=2),
        fill="tozeroy", fillcolor="rgba(42,120,214,0.10)",
        hovertemplate="%{x|%H:%M}<br>%{y:$,.0f}<extra></extra>",
    ))
    return theme.apply(figure, "Revenue per minute", height=320, legend=False,
                       y_prefix="$")


def failure_rate_chart() -> go.Figure:
    """Failure RATE only - attempts and rate are different units, so plotting
    both here would need a second y-axis. The count lives in the tooltip."""
    frame = data.realtime_payments(window_minutes)
    if frame.empty:
        return theme.apply(go.Figure(), "Payment failure rate", height=320,
                           legend=False)
    figure = go.Figure(go.Scatter(
        x=frame["minute_bucket"], y=frame["failure_rate_pct"],
        name="Failure rate", mode="lines+markers",
        line=dict(color=theme.STATUS["critical"], width=2),
        marker=dict(size=8, line=dict(width=2, color=theme.SURFACE)),
        customdata=frame[["attempts", "failed"]],
        hovertemplate="%{x|%H:%M}<br>%{y:.1f}%% failed"
                      "<br>%{customdata[1]} of %{customdata[0]} attempts<extra></extra>",
    ))
    figure.update_yaxes(ticksuffix="%")
    return theme.apply(figure, "Payment failure rate per minute", height=320,
                       legend=False)


left, right = st.columns(2)
left.plotly_chart(orders_per_minute(), width="stretch")
right.plotly_chart(failure_rate_chart(), width="stretch")


def activity_chart() -> go.Figure:
    frame = data.realtime_activity(window_minutes).sort_values("events")
    figure = go.Figure(go.Bar(
        x=frame["events"], y=frame["event_type"], orientation="h",
        marker=dict(color=theme.series_colour(2)),
        text=frame["events"], textposition="outside",
        textfont=dict(color=theme.INK_SECONDARY, size=12),
        hovertemplate="%{y}<br>%{x:,} events<extra></extra>",
    ))
    figure.update_traces(marker_cornerradius=4)
    figure.update_layout(hovermode="closest")
    figure.update_xaxes(showgrid=True, gridcolor=theme.GRIDLINE, showline=False)
    return theme.apply(figure, "Customer activity by event type", height=340,
                       legend=False)


def kpi_history() -> go.Figure:
    frame = data.realtime_kpi_history(90)
    if frame.empty:
        return theme.apply(go.Figure(), "Rolling window history", height=340,
                           legend=False)
    figure = go.Figure(go.Scatter(
        x=pd.to_datetime(frame["computed_at"]), y=frame["revenue"],
        mode="lines", name="Windowed revenue",
        line=dict(color=theme.series_colour(0), width=2),
        hovertemplate="%{x|%H:%M:%S}<br>%{y:$,.0f}<extra></extra>",
    ))
    return theme.apply(figure, "Rolling window revenue, as computed", height=340,
                       legend=False, y_prefix="$")


left, right = st.columns(2)
left.plotly_chart(activity_chart(), width="stretch")
right.plotly_chart(kpi_history(), width="stretch")

st.markdown(
    theme.note(
        "Windows are measured in <b>event time</b> - the newest event in the "
        "stream - not wall-clock time. That is what makes a replayed stream "
        "reproduce the KPIs it produced live, and it is why this page still "
        "shows data after the producer has stopped."
    ),
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Alert feed
# --------------------------------------------------------------------------- #
st.subheader("Alert feed")
alerts = data.realtime_alerts(40)
if alerts.empty:
    st.success("No failed payments or stock alerts in the stream.")
else:
    display = alerts.copy()
    display["event_ts"] = pd.to_datetime(display["event_ts"]).dt.strftime("%H:%M:%S")
    st.dataframe(
        display[["event_ts", "topic", "event_type", "status", "order_id",
                 "product_id", "customer_id", "amount", "quantity"]],
        width="stretch", hide_index=True, height=380,
    )

if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()
