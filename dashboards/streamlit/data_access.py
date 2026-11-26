"""Cached warehouse access for the dashboard.

Streamlit reruns the whole script on every interaction, so every query must be
cached or the app hammers the database on each click. ``@st.cache_data`` with a
short TTL is the right trade here: batch marts change once a pipeline run, the
real-time tables change constantly and are given a much shorter TTL.

All SQL for the dashboard lives here so a page file is layout and nothing else.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from pulse.db import get_database

BATCH_TTL = 300      # marts change once per pipeline run
LIVE_TTL = 2         # streaming tables change constantly


@st.cache_data(ttl=BATCH_TTL, show_spinner=False)
def query(sql: str) -> pd.DataFrame:
    return get_database().query(sql)


@st.cache_data(ttl=LIVE_TTL, show_spinner=False)
def live_query(sql: str) -> pd.DataFrame:
    return get_database().query(sql)


@st.cache_data(ttl=BATCH_TTL, show_spinner=False)
def warehouse_status() -> dict:
    """Is there anything to show? Drives the setup prompt on every page."""
    db = get_database()
    status = {"engine": db.config.engine, "ready": False, "stream_ready": False}
    try:
        status["ready"] = db.table_exists("gold", "mart_executive_kpis") and \
            db.row_count("gold", "mart_executive_kpis") > 0
        status["stream_ready"] = db.table_exists("ops", "stream_events") and \
            db.row_count("ops", "stream_events") > 0
    except Exception as exc:
        status["error"] = str(exc)
    return status


def require_warehouse() -> bool:
    """Render an actionable setup message instead of a stack trace."""
    status = warehouse_status()
    if status.get("ready"):
        return True
    st.warning("The warehouse has not been built yet.")
    st.code(
        "python data-generator/generate_data.py --preset small\n"
        "python -m etl.pipeline --full-refresh",
        language="bash",
    )
    if status.get("error"):
        st.caption(f"Database said: {status['error']}")
    return False


# --------------------------------------------------------------------------- #
# Batch marts
# --------------------------------------------------------------------------- #
def executive_kpis() -> pd.Series:
    frame = query("SELECT * FROM gold.mart_executive_kpis")
    return frame.iloc[0] if not frame.empty else pd.Series(dtype=object)


def daily_sales() -> pd.DataFrame:
    frame = query("SELECT * FROM gold.mart_sales_daily ORDER BY order_date")
    frame["order_date"] = pd.to_datetime(frame["order_date"])
    return frame


def monthly_sales() -> pd.DataFrame:
    frame = query("SELECT * FROM gold.mart_sales_monthly ORDER BY month_start")
    frame["month_start"] = pd.to_datetime(frame["month_start"])
    return frame


def regions() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_regional_performance ORDER BY revenue DESC")


def stores() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_store_performance ORDER BY revenue DESC")


def categories() -> pd.DataFrame:
    return query("""
        SELECT category,
               SUM(revenue)      AS revenue,
               SUM(gross_profit) AS gross_profit,
               SUM(units)        AS units,
               SUM(products)     AS products
        FROM gold.mart_category_performance
        GROUP BY category
        ORDER BY revenue DESC
    """)


def subcategories() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_category_performance ORDER BY revenue DESC")


def products() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_product_performance ORDER BY revenue DESC")


def customers() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_customer_360")


def rfm_summary() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_rfm_summary ORDER BY segment_revenue DESC")


def rfm_customers() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_rfm_segments")


def cohorts() -> pd.DataFrame:
    frame = query("SELECT * FROM gold.mart_cohort_retention")
    frame["cohort_month"] = pd.to_datetime(frame["cohort_month"])
    return frame


def retention_summary() -> pd.DataFrame:
    frame = query("SELECT * FROM gold.mart_retention_summary ORDER BY cohort_month")
    frame["cohort_month"] = pd.to_datetime(frame["cohort_month"])
    return frame


def churn_monthly() -> pd.DataFrame:
    frame = query("SELECT * FROM gold.mart_churn_monthly ORDER BY activity_month")
    frame["activity_month"] = pd.to_datetime(frame["activity_month"])
    return frame


def campaigns() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_campaign_performance ORDER BY revenue DESC")


def channels() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_channel_performance ORDER BY revenue DESC")


def acquisition_channels() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_acquisition_channel ORDER BY lifetime_revenue DESC")


def inventory() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_inventory_health ORDER BY action_priority, days_of_cover")


def inventory_weekly() -> pd.DataFrame:
    frame = query("SELECT * FROM gold.mart_inventory_weekly ORDER BY snapshot_date")
    frame["snapshot_date"] = pd.to_datetime(frame["snapshot_date"])
    return frame


def funnel() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_conversion_funnel ORDER BY step_number")


def funnel_by_device() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_funnel_by_device ORDER BY sessions DESC")


def payment_health() -> pd.DataFrame:
    frame = query("SELECT * FROM gold.mart_payment_health ORDER BY payment_date")
    frame["payment_date"] = pd.to_datetime(frame["payment_date"])
    return frame


def payment_failures() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_payment_failures ORDER BY failures DESC")


def payment_gateway_success() -> pd.DataFrame:
    return query(
        "SELECT * FROM gold.mart_payment_gateway_success "
        "ORDER BY period_order, authorisation_attempts DESC"
    )


def order_exceptions() -> pd.DataFrame:
    return query(
        "SELECT * FROM gold.mart_order_exceptions "
        "ORDER BY period_order, outcome, orders DESC"
    )


def order_exceptions_monthly() -> pd.DataFrame:
    frame = query("SELECT * FROM gold.mart_order_exceptions_monthly ORDER BY month_start")
    frame["month_start"] = pd.to_datetime(frame["month_start"])
    return frame


def revenue_local() -> pd.DataFrame:
    return query("SELECT * FROM gold.mart_revenue_local ORDER BY revenue_usd DESC")


# --------------------------------------------------------------------------- #
# Ops and streaming
# --------------------------------------------------------------------------- #
def pipeline_runs(limit: int = 40) -> pd.DataFrame:
    return query(
        f"SELECT * FROM ops.pipeline_runs ORDER BY started_at DESC LIMIT {int(limit)}"
    )


def quality_results(limit: int = 200) -> pd.DataFrame:
    return query(f"""
        SELECT * FROM ops.data_quality_results
        WHERE run_id = (SELECT run_id FROM ops.data_quality_results
                        ORDER BY checked_at DESC LIMIT 1)
        LIMIT {int(limit)}
    """)


def quality_summary() -> pd.DataFrame:
    return query(
        "SELECT * FROM ops.v_data_quality_summary ORDER BY checked_at DESC LIMIT 10"
    )


def realtime_minutes(minutes: int = 60) -> pd.DataFrame:
    frame = live_query(f"""
        WITH bounds AS (SELECT MAX(event_ts) AS latest FROM ops.stream_events)
        SELECT CAST(DATE_TRUNC('minute', e.event_ts) AS TIMESTAMP) AS minute_bucket,
               COUNT(*)                              AS orders,
               ROUND(COALESCE(SUM(e.amount), 0), 2)  AS revenue
        FROM ops.stream_events e
        CROSS JOIN bounds b
        WHERE e.topic = 'pulse.orders'
          AND e.event_ts > b.latest - INTERVAL '{int(minutes)} minutes'
        GROUP BY 1 ORDER BY 1
    """)
    if not frame.empty:
        frame["minute_bucket"] = pd.to_datetime(frame["minute_bucket"])
    return frame


def realtime_payments(minutes: int = 60) -> pd.DataFrame:
    frame = live_query(f"""
        WITH bounds AS (SELECT MAX(event_ts) AS latest FROM ops.stream_events)
        SELECT CAST(DATE_TRUNC('minute', e.event_ts) AS TIMESTAMP) AS minute_bucket,
               COUNT(*)                                    AS attempts,
               COUNT(*) FILTER (WHERE e.status = 'failed') AS failed
        FROM ops.stream_events e
        CROSS JOIN bounds b
        WHERE e.topic = 'pulse.payments'
          AND e.event_ts > b.latest - INTERVAL '{int(minutes)} minutes'
        GROUP BY 1 ORDER BY 1
    """)
    if not frame.empty:
        frame["minute_bucket"] = pd.to_datetime(frame["minute_bucket"])
        frame["failure_rate_pct"] = (
            frame["failed"] / frame["attempts"].replace(0, pd.NA) * 100
        ).round(2)
    return frame


def realtime_alerts(limit: int = 30) -> pd.DataFrame:
    return live_query(f"""
        SELECT event_ts, topic, event_type, status, order_id, product_id,
               customer_id, amount, quantity
        FROM ops.stream_events
        WHERE (topic = 'pulse.payments'  AND status = 'failed')
           OR (topic = 'pulse.inventory' AND status IN ('stockout', 'low_stock'))
        ORDER BY event_ts DESC
        LIMIT {int(limit)}
    """)


def realtime_kpi_history(limit: int = 90) -> pd.DataFrame:
    frame = live_query(
        f"SELECT * FROM ops.realtime_kpis ORDER BY computed_at DESC LIMIT {int(limit)}"
    )
    return frame.sort_values("computed_at") if not frame.empty else frame


def realtime_activity(minutes: int = 60) -> pd.DataFrame:
    return live_query(f"""
        WITH bounds AS (SELECT MAX(event_ts) AS latest FROM ops.stream_events)
        SELECT e.event_type, COUNT(*) AS events,
               COUNT(DISTINCT e.customer_id) AS customers
        FROM ops.stream_events e
        CROSS JOIN bounds b
        WHERE e.topic = 'pulse.customer_activity'
          AND e.event_ts > b.latest - INTERVAL '{int(minutes)} minutes'
        GROUP BY 1 ORDER BY events DESC
    """)
