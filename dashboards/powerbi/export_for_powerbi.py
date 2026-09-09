"""Export the gold layer for Power BI.

Power BI can connect straight to Postgres (see README.md in this folder), but a
file export is what makes the model portable: it lets a reviewer open the report
without a database, and it is exactly the shape the Azure version writes to ADLS
for Power BI to read.

    python dashboards/powerbi/export_for_powerbi.py                 # parquet
    python dashboards/powerbi/export_for_powerbi.py --format csv

Parquet by default: it keeps types (so a date stays a date and a customer_id
never becomes a float), and it is a fraction of the size.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pulse.config import PATHS                      # noqa: E402
from pulse.db import get_database                   # noqa: E402
from pulse.logging_utils import banner, get_logger  # noqa: E402

log = get_logger("powerbi.export")

# Dimensions, facts, then marts. The order is the order a modeller should load
# them in, so relationships resolve as each table lands.
DIMENSIONS = [
    "dim_date", "dim_customer", "dim_product", "dim_store",
    "dim_region", "dim_campaign", "dim_payment_method",
]
FACTS = [
    "fact_orders", "fact_sales", "fact_payments",
    "fact_inventory", "fact_customer_events",
]
MARTS = [
    "mart_sales_daily", "mart_sales_monthly", "mart_customer_360",
    "mart_rfm_segments", "mart_rfm_summary", "mart_cohort_retention",
    "mart_retention_summary", "mart_churn_monthly", "mart_product_performance",
    "mart_category_performance", "mart_campaign_performance",
    "mart_channel_performance", "mart_acquisition_channel",
    "mart_regional_performance", "mart_store_performance",
    "mart_inventory_health", "mart_inventory_weekly",
    "mart_conversion_funnel", "mart_funnel_by_device",
    "mart_payment_health", "mart_payment_failures",
    "mart_executive_kpis", "mart_revenue_local",
]


def export(output_dir: Path, file_format: str = "parquet",
           include_facts: bool = True) -> dict[str, int]:
    db = get_database()
    output_dir.mkdir(parents=True, exist_ok=True)

    tables = DIMENSIONS + (FACTS if include_facts else []) + MARTS
    counts: dict[str, int] = {}

    for table in tables:
        if not db.table_exists("gold", table):
            log.warning("gold.%s does not exist - skipped", table)
            continue
        frame = db.query(f"SELECT * FROM gold.{table}")
        path = output_dir / f"{table}.{file_format}"
        if file_format == "parquet":
            frame.to_parquet(path, index=False)
        else:
            frame.to_csv(path, index=False)
        counts[table] = len(frame)
        log.info("%-32s %9s rows -> %s", table, format(len(frame), ","), path.name)

    manifest = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "engine": db.config.engine,
        "format": file_format,
        "tables": counts,
        "total_rows": sum(counts.values()),
        "model_notes": "Relationships and measure library: see model.md and measures.dax",
    }
    (output_dir / "_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the gold layer for Power BI")
    parser.add_argument("--format", choices=["parquet", "csv"], default="parquet")
    parser.add_argument("--output", default=str(PATHS.exports / "powerbi"))
    parser.add_argument("--marts-only", action="store_true",
                        help="skip the fact tables (much smaller, aggregates only)")
    args = parser.parse_args(argv)

    print(banner("PulseAnalytics - Power BI export"))
    counts = export(Path(args.output), args.format, include_facts=not args.marts_only)

    print(f"\n{len(counts)} tables, {sum(counts.values()):,} rows -> {args.output}")
    print("\nIn Power BI Desktop: Get Data -> Folder -> point at that directory,")
    print("then apply dashboards/powerbi/theme.json and paste in measures.dax.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
