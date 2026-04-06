"""PulseAnalytics batch pipeline - the single entry point.

    python -m etl.pipeline --full-refresh          # build everything
    python -m etl.pipeline --stage marts           # rebuild gold only
    python -m etl.pipeline --quality-only          # re-run the DQ suite
    python -m etl.pipeline --full-refresh --fail-on-error   # CI mode

Stage order is fixed and each stage is independently runnable, because that is
how the pipeline is actually operated: a mart definition changes ten times for
every time the source extract does, and rebuilding gold takes seconds while
reloading bronze takes minutes.

Exit codes: 0 success, 1 a stage failed, 2 data-quality errors (with
--fail-on-error). CI distinguishes "the code broke" from "the data is bad".
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pulse.config import PATHS
from pulse.db import get_database
from pulse.logging_utils import banner, get_logger
from etl.load import load_bronze
from etl.quality import checks as dq
from etl.quality.suite import SUITES
from etl.run_context import RunContext
from etl.transform import build_layers

log = get_logger("etl.pipeline")

STAGES = ["init", "bronze", "silver", "warehouse", "marts", "quality"]


def _rows(counts: dict[str, int]) -> int:
    return sum(int(v) for v in counts.values())


def run_pipeline(
    stages: list[str],
    fail_on_error: bool = False,
    allow_network: bool = True,
    quality_suite: str = "all",
    report_path: Path | None = None,
) -> int:
    db = get_database()
    ctx = RunContext(pipeline="batch", db=db)

    print(banner("PulseAnalytics - batch pipeline"))
    log.info("run_id=%s engine=%s stages=%s", ctx.run_id, db.config.engine, ",".join(stages))

    quality_report: dq.QualityReport | None = None

    try:
        if "init" in stages:
            with ctx.stage("init schemas and bronze tables") as s:
                statements = build_layers.initialise_schemas(db)
                s["rows_out"] = sum(statements.values())
                s["message"] = f"{len(statements)} sql files"

        if "bronze" in stages:
            with ctx.stage("load bronze") as s:
                counts = load_bronze.load_all(db, allow_network=allow_network)
                s["rows_out"] = _rows(counts)
                s["message"] = ", ".join(f"{k}={v}" for k, v in counts.items())[:900]

        if "silver" in stages:
            with ctx.stage("build silver") as s:
                counts = build_layers.build_silver(db)
                s["rows_out"] = _rows(counts)
                s["message"] = ", ".join(f"{k}={v}" for k, v in counts.items())[:900]

        if "warehouse" in stages:
            with ctx.stage("build star schema") as s:
                counts = build_layers.build_warehouse(db)
                s["rows_out"] = _rows(counts)
                s["message"] = ", ".join(f"{k}={v}" for k, v in counts.items())[:900]

        if "marts" in stages:
            with ctx.stage("build gold marts") as s:
                counts = build_layers.build_marts(db)
                s["rows_out"] = _rows(counts)
                s["message"] = ", ".join(f"{k}={v}" for k, v in counts.items())[:900]

        if "quality" in stages:
            with ctx.stage("data-quality suite") as s:
                suite = SUITES[quality_suite]()
                quality_report = dq.run_checks(suite, run_id=ctx.run_id, db=db)
                s["rows_out"] = quality_report.total
                s["message"] = (
                    f"{len(quality_report.failed)} failed "
                    f"({len(quality_report.errors)} errors), "
                    f"pass rate {quality_report.pass_rate_pct}%"
                )

    except Exception:
        ctx.print_summary()
        log.error("pipeline aborted - see ops.pipeline_runs for run %s", ctx.run_id)
        return 1

    ctx.print_summary()

    if quality_report is not None:
        target = report_path or (PATHS.root / "reports" / "data_quality_report.md")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(quality_report.to_markdown(), encoding="utf-8")
        log.info("data-quality report -> %s", target)

        print(f"\nData quality: {quality_report.pass_rate_pct}% pass "
              f"({len(quality_report.failed)} of {quality_report.total} checks failed)")
        if not quality_report.failed.empty:
            for row in quality_report.failed.itertuples(index=False):
                print(f"  [{row.severity:<7}] {row.table_name}.{row.check_name} "
                      f"-> {row.failed_rows:,}/{row.total_rows:,} rows ({row.observed_value}%)")

        if fail_on_error and not quality_report.errors.empty:
            log.error("%d data-quality ERROR checks failed", len(quality_report.errors))
            return 2

    print("\nDone. Next: streamlit run dashboards/streamlit/app.py\n")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the PulseAnalytics batch pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--full-refresh", action="store_true",
                       help="run every stage from schema creation to gold marts")
    group.add_argument("--stage", choices=STAGES, action="append",
                       help="run only this stage (repeatable)")
    group.add_argument("--quality-only", action="store_true",
                       help="re-run the data-quality suite against the current warehouse")
    parser.add_argument("--suite", choices=sorted(SUITES), default="all",
                        help="which data-quality suite to run (default: all)")
    parser.add_argument("--fail-on-error", action="store_true",
                        help="exit 2 when an ERROR-severity data-quality check fails")
    parser.add_argument("--offline", action="store_true",
                        help="skip the external FX API and use the deterministic fallback")
    parser.add_argument("--report", help="path for the markdown data-quality report")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.quality_only:
        stages = ["quality"]
    elif args.stage:
        stages = [s for s in STAGES if s in set(args.stage)]
    else:
        stages = STAGES  # --full-refresh, and the default

    return run_pipeline(
        stages=stages,
        fail_on_error=args.fail_on_error,
        allow_network=not args.offline,
        quality_suite=args.suite,
        report_path=Path(args.report) if args.report else None,
    )


if __name__ == "__main__":
    sys.exit(main())
