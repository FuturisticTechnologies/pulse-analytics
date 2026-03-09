"""One database facade over DuckDB (local) and PostgreSQL (docker/production).

The SQL in ``database/`` is written in a portable subset that both engines
understand, so the same warehouse build runs in CI and against Postgres.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from pulse.config import DB, DatabaseConfig
from pulse.logging_utils import get_logger

log = get_logger("pulse.db")


def split_statements(script: str) -> list[str]:
    """Split a SQL script on top-level semicolons, ignoring quoted text."""
    without_comments = "\n".join(
        line for line in script.splitlines() if not line.strip().startswith("--")
    )
    statements: list[str] = []
    buffer: list[str] = []
    in_string = False
    for char in without_comments:
        if char == "'":
            in_string = not in_string
        if char == ";" and not in_string:
            statements.append("".join(buffer).strip())
            buffer = []
        else:
            buffer.append(char)
    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)
    return [s for s in statements if s]


class Database:
    """Thin, dependency-light wrapper: execute / query / write_frame."""

    def __init__(self, config: DatabaseConfig | None = None) -> None:
        self.config = config or DB
        if self.config.engine not in {"duckdb", "postgres"}:
            raise ValueError(f"Unsupported PULSE_DB_ENGINE={self.config.engine!r}")

    # ------------------------------------------------------------------ conn
    @contextmanager
    def connect(self):
        if self.config.is_duckdb:
            import duckdb

            self.config.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
            con = duckdb.connect(str(self.config.duckdb_path))
            try:
                yield con
            finally:
                con.close()
        else:
            import psycopg2

            con = psycopg2.connect(self.config.dsn)
            try:
                yield con
                con.commit()
            except Exception:
                con.rollback()
                raise
            finally:
                con.close()

    # --------------------------------------------------------------- execute
    def execute(self, sql: str, params: Sequence[Any] | None = None) -> None:
        with self.connect() as con:
            self._exec(con, self._adapt(sql), params)

    def _exec(self, con, sql: str, params: Sequence[Any] | None = None) -> None:
        if self.config.is_duckdb:
            con.execute(sql, list(params) if params else None)
        else:
            with con.cursor() as cur:
                cur.execute(sql, params)

    def execute_script(self, script: str) -> int:
        """Run a multi-statement SQL script; returns the statement count."""
        statements = split_statements(self._adapt(script))
        with self.connect() as con:
            for statement in statements:
                try:
                    self._exec(con, statement)
                except Exception as exc:  # pragma: no cover - surfaced to caller
                    raise RuntimeError(
                        "Failed statement:\n" + statement[:400] + "\n--> " + str(exc)
                    ) from exc
        return len(statements)

    def execute_file(self, path: str | Path) -> int:
        path = Path(path)
        log.info("running %s", path.name)
        return self.execute_script(path.read_text(encoding="utf-8"))

    # ----------------------------------------------------------------- query
    def query(self, sql: str, params: Sequence[Any] | None = None) -> pd.DataFrame:
        sql = self._adapt(sql)
        with self.connect() as con:
            if self.config.is_duckdb:
                return con.execute(sql, list(params) if params else None).df()
            return pd.read_sql_query(sql, con, params=params)

    def scalar(self, sql: str, params: Sequence[Any] | None = None) -> Any:
        frame = self.query(sql, params)
        if frame.empty:
            return None
        return frame.iloc[0, 0]

    def table_exists(self, schema: str, table: str) -> bool:
        sql = (
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = ? AND table_name = ?"
        )
        if not self.config.is_duckdb:
            sql = sql.replace("?", "%s")
        return int(self.scalar(sql, (schema, table)) or 0) > 0

    def row_count(self, schema: str, table: str) -> int:
        return int(self.scalar(f"SELECT COUNT(*) FROM {schema}.{table}") or 0)

    # ----------------------------------------------------------------- write
    def write_frame(
        self, frame: pd.DataFrame, schema: str, table: str, truncate: bool = True
    ) -> int:
        """Bulk-load a DataFrame into an existing table."""
        target = f"{schema}.{table}"
        columns = ", ".join('"' + str(c) + '"' for c in frame.columns)
        with self.connect() as con:
            if truncate:
                self._exec(con, f"DELETE FROM {target}")
            if frame.empty:
                log.warning("nothing to load into %s", target)
                return 0
            if self.config.is_duckdb:
                con.register("_stage_frame", frame)
                con.execute(
                    f"INSERT INTO {target} ({columns}) SELECT {columns} FROM _stage_frame"
                )
                con.unregister("_stage_frame")
            else:
                from psycopg2.extras import execute_batch

                placeholders = ", ".join(["%s"] * len(frame.columns))
                prepared = frame.astype(object).where(pd.notnull(frame), None)
                rows_to_write = list(prepared.itertuples(index=False, name=None))
                with con.cursor() as cur:
                    execute_batch(
                        cur,
                        f"INSERT INTO {target} ({columns}) VALUES ({placeholders})",
                        rows_to_write,
                        page_size=5000,
                    )
        log.info("loaded %s rows into %s", format(len(frame), ","), target)
        return len(frame)

    # --------------------------------------------------------------- dialect
    def _adapt(self, sql: str) -> str:
        """Translate the few tokens the two engines spell differently."""
        if self.config.is_duckdb:
            sql = sql.replace("TIMESTAMP WITHOUT TIME ZONE", "TIMESTAMP")
            sql = sql.replace("DOUBLE PRECISION", "DOUBLE")
        else:
            sql = re.sub(r"\bepoch_ms\(", "to_timestamp_ms(", sql, flags=re.I)
        return sql

    def healthcheck(self) -> dict[str, Any]:
        info: dict[str, Any] = {"engine": self.config.engine}
        try:
            info["version"] = str(self.scalar("SELECT version()"))
            info["ok"] = True
        except Exception as exc:
            info["ok"] = False
            info["error"] = str(exc)
        return info


def get_database() -> Database:
    return Database()


def rows(frame: pd.DataFrame) -> Iterable[dict]:
    return frame.to_dict(orient="records")
