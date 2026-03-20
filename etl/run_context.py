"""Run bookkeeping.

Every pipeline execution gets one ``run_id``. Every stage inside it writes a
row to ``ops.pipeline_runs`` with its status, duration and row counts. That
table is the difference between "the script printed some logs" and an operable
pipeline you can be paged about: it answers *did it run*, *how long*, *how
much*, and *what broke* without anyone reading a terminal.
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from pulse.db import Database, get_database
from pulse.logging_utils import get_logger

log = get_logger("etl.run")

PIPELINE_RUN_COLUMNS = [
    "run_id", "pipeline", "stage", "status", "started_at", "finished_at",
    "duration_sec", "rows_in", "rows_out", "message",
]


@dataclass
class StageResult:
    stage: str
    status: str
    duration_sec: float
    rows_in: int = 0
    rows_out: int = 0
    message: str = ""


@dataclass
class RunContext:
    """Tracks one end-to-end pipeline execution."""

    pipeline: str = "batch"
    db: Database = field(default_factory=get_database)
    run_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S")
                        + "-" + uuid.uuid4().hex[:6])
    stages: list[StageResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)

    # ----------------------------------------------------------------- stages
    @contextmanager
    def stage(self, name: str):
        """Time a stage, record it, and let failures propagate after logging.

        The stage yields a mutable dict so the body can report row counts:
            with ctx.stage("load bronze") as s:
                s["rows_out"] = loaded
        """
        started = datetime.now()
        payload: dict[str, object] = {"rows_in": 0, "rows_out": 0, "message": ""}
        log.info("[%s] %s ...", self.run_id, name)
        try:
            yield payload
        except Exception as exc:
            elapsed = (datetime.now() - started).total_seconds()
            self._record(name, "failed", started, elapsed, payload, str(exc)[:900])
            log.error("[%s] %s FAILED after %.2fs: %s", self.run_id, name, elapsed, exc)
            raise
        else:
            elapsed = (datetime.now() - started).total_seconds()
            self._record(name, "success", started, elapsed, payload, str(payload["message"])[:900])
            log.info(
                "[%s] %s ok in %.2fs (%s rows out)",
                self.run_id, name, elapsed, format(int(payload["rows_out"] or 0), ","),
            )

    def _record(self, name, status, started, elapsed, payload, message) -> None:
        result = StageResult(
            stage=name,
            status=status,
            duration_sec=round(elapsed, 3),
            rows_in=int(payload.get("rows_in") or 0),
            rows_out=int(payload.get("rows_out") or 0),
            message=message,
        )
        self.stages.append(result)
        self._persist(result, started)

    def _persist(self, result: StageResult, started: datetime) -> None:
        """Best-effort write to ops.pipeline_runs.

        Deliberately swallows its own errors: a broken audit table must never be
        the reason a good data load is rolled back. The failure is logged.
        """
        try:
            if not self.db.table_exists("ops", "pipeline_runs"):
                return
            frame = pd.DataFrame([{
                "run_id": self.run_id,
                "pipeline": self.pipeline,
                "stage": result.stage,
                "status": result.status,
                "started_at": started,
                "finished_at": datetime.now(),
                "duration_sec": result.duration_sec,
                "rows_in": result.rows_in,
                "rows_out": result.rows_out,
                "message": result.message,
            }])[PIPELINE_RUN_COLUMNS]
            self.db.write_frame(frame, "ops", "pipeline_runs", truncate=False)
        except Exception as exc:  # pragma: no cover - audit must not break loads
            log.warning("could not record run metadata: %s", exc)

    # ---------------------------------------------------------------- summary
    @property
    def failed(self) -> bool:
        return any(s.status == "failed" for s in self.stages)

    @property
    def duration_sec(self) -> float:
        return round((datetime.now() - self.started_at).total_seconds(), 2)

    def summary_frame(self) -> pd.DataFrame:
        return pd.DataFrame([s.__dict__ for s in self.stages])

    def print_summary(self) -> None:
        frame = self.summary_frame()
        if frame.empty:
            print("no stages ran")
            return
        print()
        print(f"Run {self.run_id} - {self.pipeline} - {self.duration_sec}s total")
        print("-" * 78)
        for row in frame.itertuples(index=False):
            flag = "OK  " if row.status == "success" else "FAIL"
            print(
                f"  {flag} {row.stage:<34} {row.duration_sec:>7.2f}s "
                f"{format(int(row.rows_out), ','):>12} rows"
            )
        print("-" * 78)
