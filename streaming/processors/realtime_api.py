"""Real-time query API.

A thin FastAPI service over the streaming tables and the gold marts. It exists
because a dashboard is not the only consumer of live numbers: an ops alerting
rule, a mobile app, or a Power BI push dataset all want JSON over HTTP, and
none of them should be given a warehouse credential.

    uvicorn streaming.processors.realtime_api:app --reload --port 8000
    curl http://localhost:8000/api/realtime/kpis

Endpoints deliberately mirror the dashboard pages one-for-one, so "what the
screen shows" and "what the API returns" cannot drift apart.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from pulse.config import STREAM
from pulse.db import get_database
from pulse.logging_utils import get_logger
from streaming.processors.kpi_processor import RealtimeKpiProcessor

log = get_logger("streaming.api")

try:
    from fastapi import FastAPI, HTTPException, Query
except ImportError as exc:  # pragma: no cover - optional dependency
    raise RuntimeError(
        "The real-time API needs FastAPI: pip install -r requirements.txt"
    ) from exc

app = FastAPI(
    title="PulseAnalytics real-time API",
    version="2.0.0",
    description=(
        "Live KPIs from the event stream and curated metrics from the gold "
        "layer. Every metric is computed by the same SQL the dashboards use."
    ),
)


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame -> JSON-safe records (timestamps as ISO strings, NaN as null)."""
    if frame.empty:
        return []
    clean = frame.copy()
    for column in clean.columns:
        if pd.api.types.is_datetime64_any_dtype(clean[column]):
            clean[column] = clean[column].dt.strftime("%Y-%m-%dT%H:%M:%S")
    return clean.astype(object).where(pd.notnull(clean), None).to_dict(orient="records")


@app.get("/health", tags=["ops"])
def health() -> dict:
    db = get_database()
    info = db.healthcheck()
    stream_rows = 0
    if info.get("ok") and db.table_exists("ops", "stream_events"):
        stream_rows = db.row_count("ops", "stream_events")
    return {
        "status": "ok" if info.get("ok") else "degraded",
        "database": info,
        "stream_backend": STREAM.backend,
        "stream_events": stream_rows,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }


@app.get("/api/realtime/kpis", tags=["realtime"])
def realtime_kpis(window_minutes: int = Query(60, ge=1, le=1440)) -> dict:
    """The live KPI tile row: orders, revenue, AOV, failure rate, sessions."""
    snapshot = RealtimeKpiProcessor(window_minutes=window_minutes).compute()
    if snapshot is None:
        return {"status": "no_data",
                "message": "No events yet - start the producer and the consumer.",
                "window_minutes": window_minutes}
    return {"status": "ok", "window_minutes": window_minutes,
            **{k: (v.isoformat(timespec="seconds") if isinstance(v, datetime) else v)
               for k, v in snapshot.items()}}


@app.get("/api/realtime/timeseries", tags=["realtime"])
def realtime_timeseries(minutes: int = Query(60, ge=1, le=1440)) -> dict:
    processor = RealtimeKpiProcessor(window_minutes=minutes)
    return {"minutes": minutes, "points": _records(processor.minute_series(minutes))}


@app.get("/api/realtime/alerts", tags=["realtime"])
def realtime_alerts(limit: int = Query(25, ge=1, le=200)) -> dict:
    processor = RealtimeKpiProcessor()
    return {"alerts": _records(processor.recent_alerts(limit))}


@app.get("/api/executive/kpis", tags=["analytics"])
def executive_kpis() -> dict:
    db = get_database()
    if not db.table_exists("gold", "mart_executive_kpis"):
        raise HTTPException(status_code=503,
                            detail="Warehouse not built - run: python -m etl.pipeline")
    frame = db.query("SELECT * FROM gold.mart_executive_kpis")
    records = _records(frame)
    if not records:
        raise HTTPException(status_code=503, detail="Executive mart is empty")
    return records[0]


@app.get("/api/sales/daily", tags=["analytics"])
def sales_daily(days: int = Query(90, ge=1, le=1000)) -> dict:
    db = get_database()
    frame = db.query(
        "SELECT * FROM gold.mart_sales_daily ORDER BY order_date DESC LIMIT " + str(int(days))
    ).sort_values("order_date")
    return {"days": len(frame), "series": _records(frame)}


@app.get("/api/sales/monthly", tags=["analytics"])
def sales_monthly() -> dict:
    db = get_database()
    return {"series": _records(
        db.query("SELECT * FROM gold.mart_sales_monthly ORDER BY month_start")
    )}


@app.get("/api/customers/segments", tags=["analytics"])
def customer_segments() -> dict:
    db = get_database()
    return {"segments": _records(
        db.query("SELECT * FROM gold.mart_rfm_summary ORDER BY segment_revenue DESC")
    )}


@app.get("/api/customers/{customer_id}", tags=["analytics"])
def customer_detail(customer_id: int) -> dict:
    db = get_database()
    sql = "SELECT * FROM gold.mart_customer_360 WHERE customer_id = ?"
    if not db.config.is_duckdb:
        sql = sql.replace("?", "%s")
    records = _records(db.query(sql, (customer_id,)))
    if not records:
        raise HTTPException(status_code=404, detail=f"customer {customer_id} not found")
    return records[0]


@app.get("/api/products/top", tags=["analytics"])
def top_products(limit: int = Query(20, ge=1, le=200)) -> dict:
    db = get_database()
    return {"products": _records(db.query(
        "SELECT product_id, sku, product_name, category, revenue, gross_profit, "
        "margin_pct, units_sold, abc_class, performance_segment "
        "FROM gold.mart_product_performance ORDER BY revenue DESC LIMIT " + str(int(limit))
    ))}


@app.get("/api/marketing/channels", tags=["analytics"])
def marketing_channels() -> dict:
    db = get_database()
    return {"channels": _records(
        db.query("SELECT * FROM gold.mart_channel_performance ORDER BY revenue DESC")
    )}


@app.get("/api/inventory/alerts", tags=["analytics"])
def inventory_alerts(limit: int = Query(50, ge=1, le=500)) -> dict:
    db = get_database()
    return {"items": _records(db.query(
        "SELECT product_id, sku, product_name, category, on_hand_units, reorder_point, "
        "days_of_cover, stock_status, action_priority "
        "FROM gold.mart_inventory_health WHERE action_priority <= 3 "
        "ORDER BY action_priority, days_of_cover LIMIT " + str(int(limit))
    ))}


@app.get("/api/quality/summary", tags=["ops"])
def quality_summary() -> dict:
    db = get_database()
    if not db.table_exists("ops", "data_quality_results"):
        return {"status": "no_data"}
    return {"runs": _records(db.query(
        "SELECT * FROM ops.v_data_quality_summary ORDER BY checked_at DESC LIMIT 10"
    ))}


@app.get("/api/pipeline/runs", tags=["ops"])
def pipeline_runs(limit: int = Query(50, ge=1, le=500)) -> dict:
    db = get_database()
    return {"runs": _records(db.query(
        "SELECT * FROM ops.pipeline_runs ORDER BY started_at DESC LIMIT " + str(int(limit))
    ))}
