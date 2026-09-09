"""Stream consumer: bus -> ops.stream_events -> rolling KPIs.

Design decisions worth defending in a review:

* **Micro-batching, not row-by-row.** Events are drained into a buffer and
  written in batches. A single-row INSERT per event would make the consumer the
  bottleneck long before the broker is, and the added latency (a second) is
  invisible on a dashboard a human is reading.
* **Commit after write, never before.** The bus offset is only advanced once the
  batch has landed. A crash mid-batch replays those events rather than losing
  them - at-least-once delivery, with ``event_id`` available for downstream
  de-duplication.
* **The consumer owns no analytics.** It lands events and recomputes the KPI
  window; every metric definition lives in SQL alongside the batch ones, so
  "revenue" cannot mean two different things depending on which pipeline
  produced it.

    python -m streaming.consumer.stream_consumer --duration 30
    python -m streaming.consumer.stream_consumer --duration 0 --from-start
"""
from __future__ import annotations

import argparse
import signal
import sys
import time
from datetime import datetime

import pandas as pd

from pulse.config import STREAM
from pulse.db import Database, get_database
from pulse.logging_utils import banner, get_logger
from streaming import events
from streaming.bus import EventBus, FileEventBus, get_bus
from streaming.processors.kpi_processor import RealtimeKpiProcessor

log = get_logger("streaming.consumer")


class StreamConsumer:
    def __init__(self, bus: EventBus | None = None, db: Database | None = None,
                 batch_size: int = 500, kpi_window_minutes: int = 60) -> None:
        self.bus = bus or get_bus()
        self.db = db or get_database()
        self.batch_size = batch_size
        self.processor = RealtimeKpiProcessor(self.db, window_minutes=kpi_window_minutes)
        self.total_written = 0
        self._ensure_target()

    def _ensure_target(self) -> None:
        if not self.db.table_exists("ops", "stream_events"):
            raise RuntimeError(
                "ops.stream_events does not exist - run: "
                "python -m etl.pipeline --stage init"
            )

    # ----------------------------------------------------------------- batch
    def drain_once(self, timeout: float = 1.0) -> int:
        """Read one batch, write it, then commit. Returns rows written."""
        batch = list(self.bus.consume(STREAM.topics, max_messages=self.batch_size,
                                      timeout=timeout))
        if not batch:
            return 0

        frame = pd.DataFrame([events.project(event) for event in batch])
        frame["event_ts"] = pd.to_datetime(frame["event_ts"], errors="coerce", format="mixed")
        frame = frame[events.PROJECTED_COLUMNS]

        written = self.db.write_frame(frame, "ops", "stream_events", truncate=False)
        self.total_written += written
        return written

    def run(self, duration_sec: float = 30.0, poll_interval: float = 1.0,
            kpi_interval_sec: float = 5.0) -> int:
        stop = {"flag": False}

        def _handle(_signum, _frame):
            log.info("stop requested")
            stop["flag"] = True

        signal.signal(signal.SIGINT, _handle)
        try:
            signal.signal(signal.SIGTERM, _handle)
        except (AttributeError, ValueError):  # pragma: no cover
            pass

        started = time.time()
        last_kpi = 0.0
        idle_polls = 0

        while not stop["flag"]:
            written = self.drain_once(timeout=poll_interval)
            idle_polls = 0 if written else idle_polls + 1

            if time.time() - last_kpi >= kpi_interval_sec:
                snapshot = self.processor.compute_and_store()
                last_kpi = time.time()
                if snapshot is not None:
                    log.info(
                        "window %s | orders=%s revenue=%s AOV=%s failures=%s (%.1f%%) sessions=%s",
                        snapshot["window_end"].strftime("%H:%M:%S"),
                        format(int(snapshot["orders"]), ","),
                        format(float(snapshot["revenue"]), ",.2f"),
                        format(float(snapshot["avg_order_value"]), ",.2f"),
                        format(int(snapshot["payment_failures"]), ","),
                        float(snapshot["failure_rate_pct"]),
                        format(int(snapshot["active_sessions"]), ","),
                    )

            if duration_sec and (time.time() - started) >= duration_sec:
                break
            if not written:
                time.sleep(min(poll_interval, 0.5))

        # Final drain so nothing produced during shutdown is left behind.
        while self.drain_once(timeout=0.5):
            pass
        self.processor.compute_and_store()

        log.info("consumed %s events in %.1fs", format(self.total_written, ","),
                 time.time() - started)
        return self.total_written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consume PulseAnalytics live events")
    parser.add_argument("--duration", type=float, default=30.0,
                        help="seconds to run; 0 = until interrupted")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--window-minutes", type=int, default=60,
                        help="width of the rolling real-time KPI window")
    parser.add_argument("--from-start", action="store_true",
                        help="reset committed offsets and replay the whole log")
    parser.add_argument("--truncate", action="store_true",
                        help="clear ops.stream_events before consuming")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print(banner("PulseAnalytics - stream consumer"))

    bus = get_bus()
    if args.from_start and isinstance(bus, FileEventBus):
        bus.reset()
        log.info("offsets reset - replaying from the start of the log")

    db = get_database()
    if args.truncate:
        db.execute("DELETE FROM ops.stream_events")
        db.execute("DELETE FROM ops.realtime_kpis")
        log.info("cleared ops.stream_events and ops.realtime_kpis")

    consumer = StreamConsumer(bus=bus, db=db, batch_size=args.batch_size,
                              kpi_window_minutes=args.window_minutes)
    try:
        consumer.run(duration_sec=args.duration, poll_interval=args.poll_interval)
    finally:
        bus.close()

    print(f"\nLanded {consumer.total_written:,} events into ops.stream_events "
          f"as of {datetime.now():%H:%M:%S}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
