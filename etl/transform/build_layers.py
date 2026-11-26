"""Transform: run the SQL that builds silver, the star schema and the marts.

The transformations themselves are SQL, in ``database/``, on purpose:

* SQL is what the warehouse actually executes - no framework in between to
  reason about when a number looks wrong at 8am;
* the same files run unchanged on DuckDB, Postgres, Synapse or Databricks SQL,
  which is what makes the Azure migration in ``infrastructure/`` a lift rather
  than a rewrite;
* an analyst who does not write Python can still read, review and fix them.

Python's job here is orchestration, ordering and row accounting.
"""
from __future__ import annotations

from pathlib import Path

from pulse import sql as sql_assets
from pulse.db import Database, get_database
from pulse.logging_utils import get_logger

log = get_logger("etl.transform")

# Tables each layer is expected to produce, used for the post-build row report
# and by the tests as a contract.
LAYER_TABLES: dict[str, list[tuple[str, str]]] = {
    "init": [
        ("bronze", "orders"), ("bronze", "order_items"), ("bronze", "customers"),
        ("ops", "pipeline_runs"), ("ops", "data_quality_results"),
    ],
    "staging": [
        ("silver", "regions"), ("silver", "stores"), ("silver", "products"),
        ("silver", "campaigns"), ("silver", "customers"), ("silver", "orders"),
        ("silver", "order_items"), ("silver", "payments"),
        ("silver", "inventory_snapshots"), ("silver", "customer_events"),
        ("silver", "fx_rates"),
    ],
    "warehouse": [
        ("gold", "dim_date"), ("gold", "dim_customer"), ("gold", "dim_product"),
        ("gold", "dim_store"), ("gold", "dim_region"), ("gold", "dim_campaign"),
        ("gold", "fact_sales"), ("gold", "fact_orders"), ("gold", "fact_payments"),
        ("gold", "fact_inventory"), ("gold", "fact_customer_events"),
    ],
    "analytics": [
        ("gold", "mart_sales_daily"), ("gold", "mart_sales_monthly"),
        ("gold", "mart_product_performance"), ("gold", "mart_customer_360"),
        ("gold", "mart_rfm_segments"), ("gold", "mart_cohort_retention"),
        ("gold", "mart_campaign_performance"), ("gold", "mart_regional_performance"),
        ("gold", "mart_inventory_health"), ("gold", "mart_conversion_funnel"),
        ("gold", "mart_payment_health"), ("gold", "mart_executive_kpis"),
        ("gold", "mart_payment_gateway_success"), ("gold", "mart_order_exceptions"),
        ("gold", "mart_order_exceptions_monthly"),
    ],
}


def run_layer(layer: str, db: Database | None = None) -> dict[str, int]:
    """Execute every .sql file in one layer, in filename order."""
    db = db or get_database()
    files: list[Path] = sql_assets.layer_files(layer)
    if not files:
        raise FileNotFoundError(f"no .sql files found for layer {layer!r}")

    statements: dict[str, int] = {}
    for path in files:
        statements[path.name] = db.execute_file(path)
    log.info("layer %-10s %d files, %d statements",
             layer, len(files), sum(statements.values()))
    return statements


def layer_row_counts(layer: str, db: Database | None = None) -> dict[str, int]:
    db = db or get_database()
    counts: dict[str, int] = {}
    for schema, table in LAYER_TABLES.get(layer, []):
        if db.table_exists(schema, table):
            counts[f"{schema}.{table}"] = db.row_count(schema, table)
    return counts


def build_silver(db: Database | None = None) -> dict[str, int]:
    run_layer("staging", db)
    return layer_row_counts("staging", db)


def build_warehouse(db: Database | None = None) -> dict[str, int]:
    run_layer("warehouse", db)
    return layer_row_counts("warehouse", db)


def build_marts(db: Database | None = None) -> dict[str, int]:
    run_layer("analytics", db)
    return layer_row_counts("analytics", db)


def initialise_schemas(db: Database | None = None) -> dict[str, int]:
    """Create schemas, bronze landing tables and the ops metadata tables."""
    return run_layer("init", db)
