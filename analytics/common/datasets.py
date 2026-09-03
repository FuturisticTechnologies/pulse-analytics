"""Curated readers over the gold layer.

Every analytical module pulls its inputs from here rather than writing its own
SQL. Two reasons:

* one place to change when a mart is renamed, instead of nine;
* the analyses are then provably reading the *same* revenue number as the
  dashboards, because they read the same mart.

Each reader raises a clear, actionable error when the warehouse has not been
built, because "KeyError: 'revenue'" is a much worse first experience than
"run: python -m etl.pipeline".
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from pulse.db import Database, get_database
from pulse.logging_utils import get_logger

log = get_logger("analytics.datasets")


class WarehouseNotBuilt(RuntimeError):
    pass


def _require(db: Database, schema: str, table: str) -> None:
    if not db.table_exists(schema, table):
        raise WarehouseNotBuilt(
            f"{schema}.{table} does not exist. Build the warehouse first:\n"
            f"    python data-generator/generate_data.py --preset small\n"
            f"    python -m etl.pipeline --full-refresh"
        )


def analysis_date(db: Database | None = None) -> date:
    """The platform's 'today' - see gold.analysis_window."""
    db = db or get_database()
    _require(db, "gold", "analysis_window")
    value = db.scalar("SELECT as_of_date FROM gold.analysis_window")
    return pd.to_datetime(value).date()


def customers(db: Database | None = None) -> pd.DataFrame:
    db = db or get_database()
    _require(db, "gold", "mart_customer_360")
    return db.query("SELECT * FROM gold.mart_customer_360")


def buyers(db: Database | None = None) -> pd.DataFrame:
    """Customers who have actually purchased - the population every customer
    model should be fitted on."""
    frame = customers(db)
    return frame[frame["orders"] > 0].copy()


def orders(db: Database | None = None) -> pd.DataFrame:
    db = db or get_database()
    _require(db, "gold", "fact_orders")
    return db.query("""
        SELECT o.order_key, o.order_date, o.order_ts, o.customer_key,
               c.customer_id, o.order_channel, o.order_status,
               o.item_count, o.net_amount, o.gross_profit, o.discount_amount,
               o.is_revenue, o.is_first_order, o.customer_order_seq,
               o.days_since_prev_order, o.campaign_key, o.region_key
        FROM gold.fact_orders o
        JOIN gold.dim_customer c ON c.customer_key = o.customer_key
    """)


def sales_lines(db: Database | None = None) -> pd.DataFrame:
    db = db or get_database()
    _require(db, "gold", "fact_sales")
    return db.query("""
        SELECT s.order_id, s.order_date, s.customer_key, s.product_key,
               p.product_id, p.product_name, p.category, p.subcategory,
               s.quantity, s.net_amount, s.gross_profit, s.is_revenue
        FROM gold.fact_sales s
        JOIN gold.dim_product p ON p.product_key = s.product_key
        WHERE s.is_revenue
    """)


def daily_sales(db: Database | None = None) -> pd.DataFrame:
    db = db or get_database()
    _require(db, "gold", "mart_sales_daily")
    frame = db.query("SELECT * FROM gold.mart_sales_daily ORDER BY order_date")
    frame["order_date"] = pd.to_datetime(frame["order_date"])
    return frame


def monthly_sales(db: Database | None = None) -> pd.DataFrame:
    db = db or get_database()
    _require(db, "gold", "mart_sales_monthly")
    frame = db.query("SELECT * FROM gold.mart_sales_monthly ORDER BY month_start")
    frame["month_start"] = pd.to_datetime(frame["month_start"])
    return frame


def products(db: Database | None = None) -> pd.DataFrame:
    db = db or get_database()
    _require(db, "gold", "mart_product_performance")
    return db.query("SELECT * FROM gold.mart_product_performance")


def inventory(db: Database | None = None) -> pd.DataFrame:
    db = db or get_database()
    _require(db, "gold", "mart_inventory_health")
    return db.query("SELECT * FROM gold.mart_inventory_health")


def campaigns(db: Database | None = None) -> pd.DataFrame:
    db = db or get_database()
    _require(db, "gold", "mart_campaign_performance")
    return db.query("SELECT * FROM gold.mart_campaign_performance")


def cohorts(db: Database | None = None) -> pd.DataFrame:
    db = db or get_database()
    _require(db, "gold", "mart_cohort_retention")
    frame = db.query("SELECT * FROM gold.mart_cohort_retention")
    frame["cohort_month"] = pd.to_datetime(frame["cohort_month"])
    return frame


def rfm(db: Database | None = None) -> pd.DataFrame:
    db = db or get_database()
    _require(db, "gold", "mart_rfm_segments")
    return db.query("SELECT * FROM gold.mart_rfm_segments")


def events(db: Database | None = None, limit: int | None = None) -> pd.DataFrame:
    db = db or get_database()
    _require(db, "gold", "fact_customer_events")
    sql = """
        SELECT event_key, event_date, event_ts, customer_key, product_key,
               event_type, funnel_step, session_id, device_class, duration_seconds
        FROM gold.fact_customer_events
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    return db.query(sql)
