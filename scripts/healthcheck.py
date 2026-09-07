"""Is the platform in a working state?

    python scripts/healthcheck.py

Checks the database connection, whether each layer has been built, whether the
last pipeline run succeeded, whether the last quality run passed, and whether
the event stream has data. Prints one line per check and exits non-zero if
anything is wrong - so it works as a container healthcheck or a cron canary,
not just as something a human reads.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pulse.config import PATHS, STREAM  # noqa: E402
from pulse.db import get_database       # noqa: E402
from pulse.logging_utils import banner  # noqa: E402

OK, WARN, FAIL = "ok", "warn", "FAIL"


def _line(status: str, label: str, detail: str = "") -> None:
    print(f"  [{status:^4}] {label:<38} {detail}")


def main() -> int:
    print(banner("PulseAnalytics - healthcheck"))
    problems = 0
    warnings = 0

    db = get_database()
    info = db.healthcheck()
    if not info.get("ok"):
        _line(FAIL, "database connection", info.get("error", ""))
        print("\nCannot continue without a database.\n")
        return 1
    _line(OK, "database connection", f"{info['engine']} {info.get('version', '')[:40]}")

    # --- raw extract -------------------------------------------------------
    raw_files = list(PATHS.raw.glob("*.csv"))
    if raw_files:
        _line(OK, "raw extract", f"{len(raw_files)} files in {PATHS.raw.name}/")
    else:
        _line(WARN, "raw extract", "none - run data-generator/generate_data.py")
        warnings += 1

    # --- layers ------------------------------------------------------------
    layers = {
        "bronze": ("bronze", "orders"),
        "silver": ("silver", "orders"),
        "star schema": ("gold", "fact_orders"),
        "gold marts": ("gold", "mart_executive_kpis"),
    }
    for label, (schema, table) in layers.items():
        if db.table_exists(schema, table):
            rows = db.row_count(schema, table)
            if rows:
                _line(OK, label, f"{schema}.{table}: {rows:,} rows")
            else:
                _line(FAIL, label, f"{schema}.{table} exists but is empty")
                problems += 1
        else:
            _line(FAIL, label, f"{schema}.{table} does not exist")
            problems += 1

    # --- last pipeline run -------------------------------------------------
    if db.table_exists("ops", "pipeline_runs") and db.row_count("ops", "pipeline_runs"):
        latest = db.query("""
            SELECT run_id, status, started_at
            FROM ops.pipeline_runs
            WHERE run_id = (SELECT run_id FROM ops.pipeline_runs
                            ORDER BY started_at DESC LIMIT 1)
        """)
        failed = int((latest["status"] == "failed").sum())
        run_id = latest.iloc[0]["run_id"]
        if failed:
            _line(FAIL, "last pipeline run", f"{run_id}: {failed} stage(s) failed")
            problems += 1
        else:
            _line(OK, "last pipeline run", f"{run_id}: {len(latest)} stages green")
    else:
        _line(WARN, "last pipeline run", "no run recorded")
        warnings += 1

    # --- data quality ------------------------------------------------------
    if db.table_exists("ops", "data_quality_results") and \
            db.row_count("ops", "data_quality_results"):
        summary = db.query(
            "SELECT * FROM ops.v_data_quality_summary ORDER BY checked_at DESC LIMIT 1"
        ).iloc[0]
        detail = (f"{summary['pass_rate_pct']}% pass, "
                  f"{int(summary['errors'])} errors, "
                  f"{int(summary['warnings'])} warnings")
        if int(summary["errors"]):
            _line(FAIL, "data quality", detail)
            problems += 1
        elif int(summary["warnings"]):
            _line(WARN, "data quality", detail)
            warnings += 1
        else:
            _line(OK, "data quality", detail)
    else:
        _line(WARN, "data quality", "no quality run recorded")
        warnings += 1

    # --- streaming ---------------------------------------------------------
    if db.table_exists("ops", "stream_events"):
        rows = db.row_count("ops", "stream_events")
        if rows:
            latest = db.scalar("SELECT MAX(event_ts) FROM ops.stream_events")
            _line(OK, "event stream", f"{rows:,} events, newest {latest}")
        else:
            _line(WARN, "event stream", "no events landed yet")
            warnings += 1
    else:
        _line(WARN, "event stream", "ops.stream_events does not exist")
        warnings += 1
    _line(OK, "stream backend", f"{STREAM.backend} ({STREAM.brokers if STREAM.backend == 'kafka' else STREAM.directory})")

    # --- verdict -----------------------------------------------------------
    print()
    if problems:
        print(f"  {problems} problem(s), {warnings} warning(s). "
              f"Rebuild with: python -m etl.pipeline --full-refresh\n")
        return 1
    if warnings:
        print(f"  Healthy, with {warnings} warning(s).\n")
        return 0
    print("  Everything is healthy.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
