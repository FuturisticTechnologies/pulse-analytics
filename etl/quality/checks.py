"""Data-quality framework.

A check is a small declarative object that knows how to count *failing rows*
and *total rows*. That shape - rather than a bare pass/fail - is what makes the
output actionable: "0.07% of customers have no email" starts a conversation,
"EMAIL CHECK FAILED" starts an argument.

Six dimensions are covered, which is the standard vocabulary a data-governance
reviewer will look for:

    completeness  is anything missing that should be there
    validity      does every value sit inside its allowed domain
    uniqueness    are keys actually unique
    consistency   do related tables agree with each other
    accuracy      do derived numbers reconcile with their inputs
    timeliness    is the data as fresh as the SLA promises

Severity separates "stop the pipeline" from "tell someone on Monday":
    error    -> fails the run (with --fail-on-error)
    warning  -> recorded, surfaced on the dashboard, does not block
    info     -> tracked for trend only
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

import pandas as pd

from pulse.db import Database, get_database
from pulse.logging_utils import get_logger

log = get_logger("etl.quality")

DIMENSIONS = ("completeness", "validity", "uniqueness", "consistency", "accuracy", "timeliness")
SEVERITIES = ("error", "warning", "info")

RESULT_COLUMNS = [
    "run_id", "checked_at", "layer", "table_name", "check_name", "dimension",
    "severity", "status", "observed_value", "threshold_value",
    "failed_rows", "total_rows", "details",
]


@dataclass
class Check:
    """One data-quality assertion.

    ``failing_sql`` must return a single row with columns ``failed_rows`` and
    ``total_rows``. Expressing every check in that one shape means the runner
    needs no special cases and new checks are three lines of SQL.
    """

    name: str
    layer: str
    table: str
    dimension: str
    failing_sql: str
    severity: str = "error"
    threshold_pct: float = 0.0        # max tolerated % of failing rows
    details: str = ""

    def __post_init__(self) -> None:
        if self.dimension not in DIMENSIONS:
            raise ValueError(f"{self.name}: unknown dimension {self.dimension!r}")
        if self.severity not in SEVERITIES:
            raise ValueError(f"{self.name}: unknown severity {self.severity!r}")

    def run(self, db: Database) -> dict:
        frame = db.query(self.failing_sql)
        failed = int(frame["failed_rows"].iloc[0] or 0) if not frame.empty else 0
        total = int(frame["total_rows"].iloc[0] or 0) if not frame.empty else 0
        observed = round(failed / total * 100, 4) if total else 0.0
        passed = observed <= self.threshold_pct
        return {
            "layer": self.layer,
            "table_name": self.table,
            "check_name": self.name,
            "dimension": self.dimension,
            "severity": self.severity,
            "status": "pass" if passed else "fail",
            "observed_value": observed,
            "threshold_value": self.threshold_pct,
            "failed_rows": failed,
            "total_rows": total,
            "details": self.details,
        }


# --------------------------------------------------------------------------- #
# Check constructors - the vocabulary the suite is written in.
# --------------------------------------------------------------------------- #
def not_null(layer: str, table: str, column: str, *, severity: str = "error",
             threshold_pct: float = 0.0) -> Check:
    return Check(
        name=f"{table}.{column} is not null",
        layer=layer, table=table, dimension="completeness",
        severity=severity, threshold_pct=threshold_pct,
        failing_sql=(
            f"SELECT COUNT(*) FILTER (WHERE {column} IS NULL) AS failed_rows, "
            f"COUNT(*) AS total_rows FROM {layer}.{table}"
        ),
        details=f"Rows where {column} is missing.",
    )


def unique(layer: str, table: str, column: str, *, severity: str = "error") -> Check:
    return Check(
        name=f"{table}.{column} is unique",
        layer=layer, table=table, dimension="uniqueness", severity=severity,
        failing_sql=(
            f"SELECT COALESCE(SUM(n - 1), 0) AS failed_rows, "
            f"COALESCE(SUM(n), 0) AS total_rows FROM ("
            f"  SELECT {column}, COUNT(*) AS n FROM {layer}.{table}"
            f"  WHERE {column} IS NOT NULL GROUP BY {column}"
            f") d"
        ),
        details=f"Duplicate values of {column}.",
    )


def accepted_values(layer: str, table: str, column: str, values: list[str],
                    *, severity: str = "error") -> Check:
    literal = ", ".join("'" + v.replace("'", "''") + "'" for v in values)
    return Check(
        name=f"{table}.{column} in accepted set",
        layer=layer, table=table, dimension="validity", severity=severity,
        failing_sql=(
            f"SELECT COUNT(*) FILTER (WHERE {column} IS NOT NULL "
            f"                        AND {column} NOT IN ({literal})) AS failed_rows, "
            f"COUNT(*) AS total_rows FROM {layer}.{table}"
        ),
        details=f"Allowed: {', '.join(values)}.",
    )


def expression_holds(name: str, layer: str, table: str, expression: str,
                     dimension: str = "validity", *, severity: str = "error",
                     threshold_pct: float = 0.0, details: str = "") -> Check:
    """Generic: every row must satisfy ``expression``."""
    return Check(
        name=name, layer=layer, table=table, dimension=dimension,
        severity=severity, threshold_pct=threshold_pct,
        failing_sql=(
            f"SELECT COUNT(*) FILTER (WHERE NOT ({expression})) AS failed_rows, "
            f"COUNT(*) AS total_rows FROM {layer}.{table}"
        ),
        details=details or f"Rows violating: {expression}",
    )


def foreign_key(layer: str, table: str, column: str,
                parent_layer: str, parent_table: str, parent_column: str,
                *, severity: str = "error", threshold_pct: float = 0.0) -> Check:
    return Check(
        name=f"{table}.{column} references {parent_table}",
        layer=layer, table=table, dimension="consistency",
        severity=severity, threshold_pct=threshold_pct,
        failing_sql=(
            f"SELECT COUNT(*) FILTER (WHERE c.{column} IS NOT NULL "
            f"                        AND p.{parent_column} IS NULL) AS failed_rows, "
            f"COUNT(*) AS total_rows "
            f"FROM {layer}.{table} c "
            f"LEFT JOIN {parent_layer}.{parent_table} p "
            f"       ON p.{parent_column} = c.{column}"
        ),
        details=f"Orphan {column} values with no matching {parent_table}.",
    )


def row_count_at_least(layer: str, table: str, minimum: int,
                       *, severity: str = "error") -> Check:
    return Check(
        name=f"{table} has at least {minimum} rows",
        layer=layer, table=table, dimension="completeness", severity=severity,
        failing_sql=(
            f"SELECT CASE WHEN COUNT(*) < {minimum} THEN 1 ELSE 0 END AS failed_rows, "
            f"1 AS total_rows FROM {layer}.{table}"
        ),
        details=f"Table must not be empty (minimum {minimum} rows).",
    )


def reconciles(name: str, layer: str, table: str, sql: str, tolerance_pct: float = 0.01,
               *, severity: str = "error", details: str = "") -> Check:
    """Accuracy check: two independently computed numbers must agree.

    ``sql`` returns one row with ``left_value`` and ``right_value``.
    """
    fraction = tolerance_pct / 100.0
    return Check(
        name=name, layer=layer, table=table, dimension="accuracy",
        severity=severity, threshold_pct=0.0,
        failing_sql=(
            "SELECT CASE WHEN ABS(COALESCE(left_value, 0) - COALESCE(right_value, 0)) "
            f"            > GREATEST(ABS(COALESCE(right_value, 0)) * {fraction}, 0.01) "
            "            THEN 1 ELSE 0 END AS failed_rows, "
            "1 AS total_rows FROM (" + sql + ") r"
        ),
        details=details or (
            f"Two independent computations of the same measure must agree "
            f"within {tolerance_pct}%."
        ),
    )


def fresh_within_days(layer: str, table: str, column: str, max_age_days: int,
                      reference_sql: str, *, severity: str = "warning") -> Check:
    """Timeliness: the newest row must be no older than ``max_age_days``.

    ``reference_sql`` supplies "now" - the analysis anchor for a static demo
    dataset, or CURRENT_DATE for a live feed.
    """
    return Check(
        name=f"{table} is fresh within {max_age_days} days",
        layer=layer, table=table, dimension="timeliness", severity=severity,
        failing_sql=(
            f"SELECT CASE WHEN CAST(({reference_sql}) - CAST(MAX({column}) AS DATE) AS INTEGER) "
            f"            > {max_age_days} THEN 1 ELSE 0 END AS failed_rows, "
            f"1 AS total_rows FROM {layer}.{table}"
        ),
        details=f"Newest {column} must be within {max_age_days} days of the analysis date.",
    )


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
@dataclass
class QualityReport:
    run_id: str
    results: pd.DataFrame
    checked_at: datetime = field(default_factory=datetime.now)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def failed(self) -> pd.DataFrame:
        return self.results[self.results["status"] == "fail"]

    @property
    def errors(self) -> pd.DataFrame:
        return self.failed[self.failed["severity"] == "error"]

    @property
    def warnings(self) -> pd.DataFrame:
        return self.failed[self.failed["severity"] == "warning"]

    @property
    def pass_rate_pct(self) -> float:
        if not self.total:
            return 100.0
        passed = int((self.results["status"] == "pass").sum())
        return round(passed / self.total * 100, 1)

    def to_markdown(self) -> str:
        lines = [
            "# Data-quality report",
            "",
            f"* Run: `{self.run_id}`",
            f"* Checked at: {self.checked_at:%Y-%m-%d %H:%M:%S}",
            f"* Checks: **{self.total}** - passed **{self.total - len(self.failed)}**, "
            f"failed **{len(self.failed)}** ({len(self.errors)} errors, "
            f"{len(self.warnings)} warnings)",
            f"* Pass rate: **{self.pass_rate_pct}%**",
            "",
            "## By dimension",
            "",
            "| Dimension | Checks | Passed | Failed |",
            "| --- | ---: | ---: | ---: |",
        ]
        for dimension, group in self.results.groupby("dimension"):
            passed = int((group["status"] == "pass").sum())
            lines.append(
                f"| {dimension} | {len(group)} | {passed} | {len(group) - passed} |"
            )

        lines += ["", "## Failing checks", ""]
        if self.failed.empty:
            lines.append("None. Every check passed.")
        else:
            lines += [
                "| Severity | Layer | Table | Check | Failed | Total | % | Threshold |",
                "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
            ]
            for row in self.failed.itertuples(index=False):
                lines.append(
                    f"| {row.severity} | {row.layer} | {row.table_name} | {row.check_name} "
                    f"| {row.failed_rows:,} | {row.total_rows:,} "
                    f"| {row.observed_value}% | {row.threshold_value}% |"
                )

        lines += ["", "## All checks", "",
                  "| Status | Dimension | Table | Check | Observed | Threshold |",
                  "| --- | --- | --- | --- | ---: | ---: |"]
        for row in self.results.itertuples(index=False):
            mark = "pass" if row.status == "pass" else "**FAIL**"
            lines.append(
                f"| {mark} | {row.dimension} | {row.table_name} | {row.check_name} "
                f"| {row.observed_value}% | {row.threshold_value}% |"
            )
        return "\n".join(lines) + "\n"


def run_checks(checks: list[Check], run_id: str, db: Database | None = None,
               persist: bool = True,
               on_error: Callable[[Check, Exception], None] | None = None) -> QualityReport:
    """Execute every check, persist the results, return a report.

    A check that raises is recorded as a failure rather than aborting the suite:
    one broken assertion must not hide the other forty.
    """
    db = db or get_database()
    checked_at = datetime.now()
    rows: list[dict] = []

    for check in checks:
        try:
            result = check.run(db)
        except Exception as exc:
            if on_error:
                on_error(check, exc)
            log.error("check %r could not run: %s", check.name, exc)
            result = {
                "layer": check.layer, "table_name": check.table,
                "check_name": check.name, "dimension": check.dimension,
                "severity": check.severity, "status": "fail",
                "observed_value": 100.0, "threshold_value": check.threshold_pct,
                "failed_rows": 0, "total_rows": 0,
                "details": f"check could not execute: {exc}"[:900],
            }
        result["run_id"] = run_id
        result["checked_at"] = checked_at
        rows.append(result)

    results = pd.DataFrame(rows)[RESULT_COLUMNS] if rows else pd.DataFrame(columns=RESULT_COLUMNS)

    if persist and not results.empty and db.table_exists("ops", "data_quality_results"):
        db.write_frame(results, "ops", "data_quality_results", truncate=False)

    report = QualityReport(run_id=run_id, results=results, checked_at=checked_at)
    log.info("quality: %d checks, %d failed (%d error / %d warning), pass rate %.1f%%",
             report.total, len(report.failed), len(report.errors),
             len(report.warnings), report.pass_rate_pct)
    return report
