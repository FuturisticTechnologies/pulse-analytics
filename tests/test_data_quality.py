"""The data-quality framework, and the suite it runs.

Two levels here:

* the **framework** - a check must count failing rows correctly, must respect
  its threshold, and must survive its own SQL being broken;
* the **suite** - it must actually pass against a clean build, and it must
  actually FAIL when a defect is introduced. A quality suite that has never been
  seen to fail is not evidence of anything.
"""
from __future__ import annotations

import uuid

import pandas as pd
import pytest

from etl.quality import checks as dq
from etl.quality.suite import bronze_checks, full_suite, gold_checks, silver_checks


# --------------------------------------------------------------------------- #
# Framework
# --------------------------------------------------------------------------- #
def test_not_null_counts_actual_nulls(db):
    check = dq.not_null("bronze", "customers", "email", severity="warning",
                        threshold_pct=100)
    result = check.run(db)
    expected = db.scalar("SELECT COUNT(*) FROM bronze.customers WHERE email IS NULL")
    assert result["failed_rows"] == expected
    assert result["total_rows"] == db.row_count("bronze", "customers")


def test_threshold_decides_pass_or_fail(db):
    strict = dq.not_null("bronze", "customers", "email", threshold_pct=0.0)
    lenient = dq.not_null("bronze", "customers", "email", threshold_pct=100.0)
    assert strict.run(db)["status"] == "fail"
    assert lenient.run(db)["status"] == "pass"


def test_unique_check_finds_the_replayed_orders(db):
    assert dq.unique("bronze", "orders", "order_id").run(db)["failed_rows"] > 0
    assert dq.unique("silver", "orders", "order_id").run(db)["failed_rows"] == 0


def test_accepted_values_rejects_a_value_outside_the_domain(db):
    good = dq.accepted_values("silver", "orders", "status",
                              ["completed", "cancelled", "returned", "pending"])
    bad = dq.accepted_values("silver", "orders", "status", ["completed"])
    assert good.run(db)["status"] == "pass"
    assert bad.run(db)["status"] == "fail"


def test_foreign_key_check_finds_orphans(db):
    clean = dq.foreign_key("silver", "orders", "customer_id",
                           "silver", "customers", "customer_id")
    assert clean.run(db)["failed_rows"] == 0


def test_reconciliation_check_compares_two_computations(db):
    agreeing = dq.reconciles("agrees", "gold", "fact_sales", """
        SELECT (SELECT SUM(net_amount) FROM gold.fact_sales  WHERE is_revenue) AS left_value,
               (SELECT SUM(net_amount) FROM gold.fact_orders WHERE is_revenue) AS right_value
    """)
    disagreeing = dq.reconciles("disagrees", "gold", "fact_sales", """
        SELECT (SELECT SUM(net_amount) FROM gold.fact_sales WHERE is_revenue) AS left_value,
               (SELECT SUM(net_amount) * 2 FROM gold.fact_orders WHERE is_revenue) AS right_value
    """)
    assert agreeing.run(db)["status"] == "pass"
    assert disagreeing.run(db)["status"] == "fail"


def test_a_broken_check_is_recorded_as_a_failure_not_an_exception(db):
    """One broken assertion must not hide the other forty."""
    broken = dq.Check(
        name="references a table that does not exist",
        layer="gold", table="nowhere", dimension="validity",
        failing_sql="SELECT COUNT(*) AS failed_rows, 1 AS total_rows FROM gold.nowhere",
    )
    report = dq.run_checks([broken, dq.row_count_at_least("gold", "fact_orders", 1)],
                           run_id="broken-check-test", db=db, persist=False)
    assert report.total == 2
    assert len(report.failed) == 1
    assert "could not execute" in report.results.iloc[0]["details"]


def test_check_rejects_an_unknown_dimension():
    with pytest.raises(ValueError):
        dq.Check(name="x", layer="gold", table="t", dimension="vibes",
                 failing_sql="SELECT 0 AS failed_rows, 1 AS total_rows")


# --------------------------------------------------------------------------- #
# The suite
# --------------------------------------------------------------------------- #
def test_the_full_suite_passes_against_a_clean_build(db):
    report = dq.run_checks(full_suite(), run_id="suite-test", db=db, persist=False)
    failures = report.failed
    assert failures.empty, (
        "unexpected quality failures:\n"
        + failures[["severity", "table_name", "check_name",
                    "failed_rows", "total_rows", "observed_value"]].to_string()
    )


def test_the_suite_covers_every_quality_dimension():
    dimensions = {check.dimension for check in full_suite()}
    assert dimensions == set(dq.DIMENSIONS), (
        f"uncovered dimensions: {set(dq.DIMENSIONS) - dimensions}"
    )


def test_the_suite_covers_every_layer():
    assert {c.layer for c in bronze_checks()} == {"bronze"}
    assert {c.layer for c in silver_checks()} == {"silver"}
    assert {c.layer for c in gold_checks()} == {"gold"}


def test_the_suite_would_catch_a_real_defect(db):
    """Introduce a genuine defect, confirm the suite fails, then repair it.

    Without this test the suite is unfalsifiable: it has only ever been seen to
    pass, so its passing means nothing.
    """
    check = dq.unique("gold", "dim_customer", "customer_key")
    assert check.run(db)["status"] == "pass"

    db.execute("""
        INSERT INTO gold.dim_customer
        SELECT * FROM gold.dim_customer WHERE customer_key <> -1 LIMIT 1
    """)
    try:
        assert check.run(db)["status"] == "fail", \
            "the uniqueness check did not notice a duplicated dimension row"
    finally:
        # Restore the warehouse for every later test in the session.
        db.execute("""
            DELETE FROM gold.dim_customer
            WHERE customer_key IN (
                SELECT customer_key FROM gold.dim_customer
                GROUP BY customer_key HAVING COUNT(*) > 1
            )
        """)
        db.execute("""
            INSERT INTO gold.dim_customer
            SELECT
                CAST(ROW_NUMBER() OVER (ORDER BY c.customer_id) AS INTEGER),
                c.customer_id, c.full_name, c.email, c.signup_date, c.signup_month,
                COALESCE(r.region_key, -1), c.city, c.acquisition_channel,
                c.age_band, c.gender, c.loyalty_tier, c.marketing_opt_in,
                c.is_missing_email
            FROM silver.customers c
            LEFT JOIN gold.dim_region r ON r.region_id = c.region_id
            WHERE c.customer_id NOT IN (SELECT customer_id FROM gold.dim_customer)
        """)
    assert check.run(db)["status"] == "pass"


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def test_report_renders_markdown(db):
    report = dq.run_checks(bronze_checks(), run_id="markdown-test", db=db,
                           persist=False)
    markdown = report.to_markdown()
    assert "# Data-quality report" in markdown
    assert "## By dimension" in markdown
    assert "markdown-test" in markdown


def test_results_persist_to_the_ops_table(db):
    # A unique run_id per invocation: ops.data_quality_results is append-only
    # and deliberately survives a rebuild, so a fixed id would accumulate rows
    # across runs and make this test pass once and fail forever after.
    run_id = f"persist-test-{uuid.uuid4().hex[:8]}"

    before = db.row_count("ops", "data_quality_results")
    dq.run_checks(bronze_checks(), run_id=run_id, db=db, persist=True)
    after = db.row_count("ops", "data_quality_results")
    assert after > before

    stored = db.query(
        f"SELECT * FROM ops.data_quality_results WHERE run_id = '{run_id}'"
    )
    assert len(stored) == len(bronze_checks())
    assert set(stored.columns) == set(dq.RESULT_COLUMNS)


def test_pass_rate_is_computed_from_the_results(db):
    frame = pd.DataFrame([
        {"status": "pass", "severity": "error", "dimension": "validity"},
        {"status": "fail", "severity": "error", "dimension": "validity"},
        {"status": "fail", "severity": "warning", "dimension": "validity"},
        {"status": "pass", "severity": "error", "dimension": "validity"},
    ])
    report = dq.QualityReport(run_id="arithmetic", results=frame)
    assert report.pass_rate_pct == 50.0
    assert len(report.errors) == 1
    assert len(report.warnings) == 1
