"""Rolling real-time KPI processor.

Computes a sliding window over ``ops.stream_events`` and persists one row per
computation into ``ops.realtime_kpis``.

Why a table rather than an in-memory counter:

* the dashboard, the API and the consumer are three separate processes - shared
  state has to live somewhere both durable and queryable;
* restarting the consumer must not blank the dashboard;
* keeping the history of the window lets the live page draw a trend line, which
  is the difference between a number and a signal.

The window is measured in **event time**, not wall-clock time, so replaying a
recorded stream produces exactly the same KPIs it produced live.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from pulse.db import Database, get_database
from pulse.logging_utils import get_logger

log = get_logger("streaming.kpi")

KPI_COLUMNS = [
    "window_start", "window_end", "orders", "revenue", "avg_order_value",
    "payment_attempts", "payment_failures", "failure_rate_pct",
    "active_sessions", "stockout_alerts", "computed_at",
]

WINDOW_SQL = """
WITH bounds AS (
    SELECT MAX(event_ts) AS window_end
    FROM ops.stream_events
),
scoped AS (
    SELECT e.*
    FROM ops.stream_events e
    CROSS JOIN bounds b
    WHERE e.event_ts > b.window_end - INTERVAL '{minutes} minutes'
)
SELECT
    (SELECT window_end FROM bounds)                                     AS window_end,
    COUNT(*) FILTER (WHERE topic = 'pulse.orders')                      AS orders,
    COALESCE(SUM(amount) FILTER (WHERE topic = 'pulse.orders'), 0)      AS revenue,
    COUNT(*) FILTER (WHERE topic = 'pulse.payments')                    AS payment_attempts,
    COUNT(*) FILTER (WHERE topic = 'pulse.payments' AND status = 'failed')
                                                                        AS payment_failures,
    COALESCE(SUM(amount) FILTER (WHERE topic = 'pulse.payments' AND status = 'failed'), 0)
                                                                        AS amount_at_risk,
    COUNT(DISTINCT customer_id) FILTER (WHERE topic = 'pulse.customer_activity')
                                                                        AS active_sessions,
    COUNT(*) FILTER (WHERE topic = 'pulse.inventory' AND status = 'stockout')
                                                                        AS stockout_alerts,
    COUNT(*) FILTER (WHERE topic = 'pulse.inventory' AND status = 'low_stock')
                                                                        AS low_stock_alerts,
    COUNT(DISTINCT customer_id) FILTER (WHERE topic = 'pulse.orders')   AS buying_customers
FROM scoped
"""


class RealtimeKpiProcessor:
    def __init__(self, db: Database | None = None, window_minutes: int = 60) -> None:
        self.db = db or get_database()
        self.window_minutes = window_minutes

    def compute(self) -> dict | None:
        """Return the current window's KPIs, or None if the stream is empty."""
        frame = self.db.query(WINDOW_SQL.format(minutes=self.window_minutes))
        if frame.empty or pd.isna(frame["window_end"].iloc[0]):
            return None

        row = frame.iloc[0]
        window_end = pd.to_datetime(row["window_end"]).to_pydatetime()
        orders = int(row["orders"] or 0)
        revenue = float(row["revenue"] or 0.0)
        attempts = int(row["payment_attempts"] or 0)
        failures = int(row["payment_failures"] or 0)

        return {
            "window_start": window_end - timedelta(minutes=self.window_minutes),
            "window_end": window_end,
            "orders": orders,
            "revenue": round(revenue, 2),
            "avg_order_value": round(revenue / orders, 2) if orders else 0.0,
            "payment_attempts": attempts,
            "payment_failures": failures,
            "failure_rate_pct": round(failures / attempts * 100, 2) if attempts else 0.0,
            "active_sessions": int(row["active_sessions"] or 0),
            "stockout_alerts": int(row["stockout_alerts"] or 0),
            "computed_at": datetime.now(),
            # Extra context the API exposes but the KPI table does not store.
            "amount_at_risk": round(float(row["amount_at_risk"] or 0.0), 2),
            "low_stock_alerts": int(row["low_stock_alerts"] or 0),
            "buying_customers": int(row["buying_customers"] or 0),
        }

    def compute_and_store(self) -> dict | None:
        snapshot = self.compute()
        if snapshot is None:
            return None
        frame = pd.DataFrame([{k: snapshot[k] for k in KPI_COLUMNS}])
        self.db.write_frame(frame, "ops", "realtime_kpis", truncate=False)
        return snapshot

    # ------------------------------------------------------------- readers
    def history(self, limit: int = 120) -> pd.DataFrame:
        return self.db.query(
            "SELECT * FROM ops.realtime_kpis ORDER BY computed_at DESC LIMIT " + str(int(limit))
        ).sort_values("computed_at")

    def latest(self) -> dict | None:
        frame = self.db.query(
            "SELECT * FROM ops.realtime_kpis ORDER BY computed_at DESC LIMIT 1"
        )
        return None if frame.empty else frame.iloc[0].to_dict()

    def minute_series(self, minutes: int = 60) -> pd.DataFrame:
        """Per-minute orders and revenue - the live sparkline."""
        return self.db.query(f"""
            WITH bounds AS (SELECT MAX(event_ts) AS latest FROM ops.stream_events)
            SELECT
                CAST(DATE_TRUNC('minute', e.event_ts) AS TIMESTAMP) AS minute_bucket,
                COUNT(*)                                            AS orders,
                ROUND(COALESCE(SUM(e.amount), 0), 2)                AS revenue
            FROM ops.stream_events e
            CROSS JOIN bounds b
            WHERE e.topic = 'pulse.orders'
              AND e.event_ts > b.latest - INTERVAL '{int(minutes)} minutes'
            GROUP BY 1
            ORDER BY 1
        """)

    def recent_alerts(self, limit: int = 25) -> pd.DataFrame:
        """The operations feed: failed payments and stock alerts, newest first."""
        return self.db.query(f"""
            SELECT event_ts, topic, event_type, status,
                   order_id, product_id, customer_id, amount, quantity
            FROM ops.stream_events
            WHERE (topic = 'pulse.payments'  AND status = 'failed')
               OR (topic = 'pulse.inventory' AND status IN ('stockout', 'low_stock'))
            ORDER BY event_ts DESC
            LIMIT {int(limit)}
        """)
