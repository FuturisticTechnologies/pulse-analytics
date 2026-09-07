"""One command that builds and demonstrates the whole platform.

    python scripts/run_demo.py

Runs, in order: generate data -> build the warehouse -> run the data-quality
suite -> run every analytical model -> backfill and consume a live event stream
-> export for Power BI. Then prints what to open.

Exists because "clone it and see it work" should be one command, not a page of
instructions - and because a single script that runs every component is the
fastest way to notice that one of them has broken.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pulse.logging_utils import banner  # noqa: E402


def run(description: str, command: list[str], optional: bool = False) -> bool:
    """Run one step, echoing the command so it can be copied and rerun."""
    print(f"\n{'=' * 78}\n  {description}\n  $ {' '.join(command)}\n{'=' * 78}")
    started = time.perf_counter()
    result = subprocess.run([sys.executable, *command], cwd=ROOT)
    elapsed = time.perf_counter() - started

    if result.returncode == 0:
        print(f"\n  -> ok ({elapsed:.1f}s)")
        return True
    if optional:
        print(f"\n  -> skipped: exit {result.returncode} ({elapsed:.1f}s). "
              f"Not fatal - continuing.")
        return True
    print(f"\n  -> FAILED: exit {result.returncode} ({elapsed:.1f}s)")
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and demonstrate PulseAnalytics")
    parser.add_argument("--preset", default="small",
                        choices=["small", "medium", "large"],
                        help="dataset size (small is a few seconds, medium a minute)")
    parser.add_argument("--skip-data", action="store_true",
                        help="reuse the existing data/raw extract")
    parser.add_argument("--skip-stream", action="store_true")
    parser.add_argument("--stream-minutes", type=int, default=45,
                        help="minutes of live-event history to backfill")
    args = parser.parse_args(argv)

    print(banner("PulseAnalytics - full demo build"))
    started = time.perf_counter()

    steps: list[tuple[str, list[str], bool]] = []
    if not args.skip_data:
        steps.append((
            f"1. Generate two years of history ({args.preset} preset)",
            ["data-generator/generate_data.py", "--preset", args.preset],
            False,
        ))
    steps += [
        ("2. Build the warehouse and run the data-quality suite",
         ["-m", "etl.pipeline", "--full-refresh"], False),
        ("3. Run every analytical model and write the insight report",
         ["-m", "analytics.run_analytics"], False),
    ]
    if not args.skip_stream:
        steps += [
            (f"4. Emit {args.stream_minutes} minutes of live-event history",
             ["-m", "streaming.producer.event_producer",
              "--backfill-minutes", str(args.stream_minutes)], False),
            ("5. Consume the stream into the warehouse",
             ["-m", "streaming.consumer.stream_consumer",
              "--duration", "12", "--from-start", "--truncate"], False),
        ]
    steps.append((
        "6. Export the gold layer for Power BI",
        ["dashboards/powerbi/export_for_powerbi.py"], True,
    ))

    for description, command, optional in steps:
        if not run(description, command, optional):
            print("\nThe demo stopped early. The command above is the one to debug.")
            return 1

    elapsed = time.perf_counter() - started
    print(f"\n{'=' * 78}")
    print(f"  Built in {elapsed:.0f}s. What to open:")
    print(f"{'=' * 78}")
    print("""
  Dashboards      python -m streamlit run dashboards/streamlit/app.py
                  -> http://localhost:8501

  Real-time API   python -m uvicorn streaming.processors.realtime_api:app --port 8000
                  -> http://localhost:8000/docs

  Live stream     terminal 1: python -m streaming.producer.event_producer --rate 8 --duration 0
                  terminal 2: python -m streaming.consumer.stream_consumer --duration 0
                  then open the Real-time page and turn on auto refresh

  Written output  reports/insight_report.md        the analyst's deliverable
                  reports/data_quality_report.md   what the DQ suite found
                  data/exports/                    CSV extracts per analysis
                  data/exports/powerbi/            parquet for Power BI
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
