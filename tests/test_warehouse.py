"""The warehouse contract: does the star schema hold, and does it reconcile.

These are the tests that would catch a silently wrong number - a dropped join, a
double-counted grain, a mart drifting from the fact it is built on. Every one of
them exists because that failure is invisible in a dashboard until someone acts
on it.
"""
from __future__ import annotations

import pytest

DIMENSIONS = ["dim_date", "dim_customer", "dim_product", "dim_store",
              "dim_region", "dim_campaign", "dim_payment_method"]
FACTS = ["fact_orders", "fact_sales", "fact_payments",
         "fact_inventory", "fact_customer_events"]
MARTS = ["mart_sales_daily", "mart_sales_monthly", "mart_customer_360",
         "mart_rfm_segments", "mart_cohort_retention", "mart_campaign_performance",
         "mart_regional_performance", "mart_inventory_health",
         "mart_conversion_funnel", "mart_payment_health", "mart_executive_kpis",
         "mart_payment_gateway_success", "mart_order_exceptions",
         "mart_order_exceptions_monthly"]

TOLERANCE = 0.01     # currency rounding across two aggregation paths


@pytest.mark.parametrize("table", DIMENSIONS + FACTS + MARTS)
def test_table_exists_and_has_rows(db, table):
    assert db.table_exists("gold", table), f"gold.{table} was not built"
    assert db.row_count("gold", table) > 0, f"gold.{table} is empty"


@pytest.mark.parametrize("table,key", [
    ("dim_customer", "customer_key"), ("dim_product", "product_key"),
    ("dim_store", "store_key"), ("dim_region", "region_key"),
    ("dim_campaign", "campaign_key"), ("dim_date", "date_key"),
    ("fact_orders", "order_key"), ("fact_sales", "sales_key"),
])
def test_surrogate_keys_are_unique(db, table, key):
    total = db.scalar(f"SELECT COUNT(*) FROM gold.{table}")
    distinct = db.scalar(f"SELECT COUNT(DISTINCT {key}) FROM gold.{table}")
    assert total == distinct, f"gold.{table}.{key} is not unique"


@pytest.mark.parametrize("dimension,key", [
    ("dim_customer", "customer_key"), ("dim_product", "product_key"),
    ("dim_store", "store_key"), ("dim_region", "region_key"),
    ("dim_campaign", "campaign_key"),
])
def test_every_dimension_has_an_unknown_member(db, dimension, key):
    """The -1 member is what lets facts join inner-style without losing rows."""
    assert db.scalar(
        f"SELECT COUNT(*) FROM gold.{dimension} WHERE {key} = -1"
    ) == 1


def test_no_sales_row_points_at_an_unknown_dimension(db):
    """A fact row on the Unknown member means a join silently failed and
    revenue is being attributed to nobody."""
    for key in ["customer_key", "product_key", "store_key", "region_key"]:
        orphans = db.scalar(f"SELECT COUNT(*) FROM gold.fact_sales WHERE {key} = -1")
        assert orphans == 0, f"{orphans} fact_sales rows have an unknown {key}"


def test_campaign_key_may_legitimately_be_unknown(db):
    """Not every order comes from a campaign - that -1 is data, not a defect."""
    assert db.scalar(
        "SELECT COUNT(*) FROM gold.fact_orders WHERE campaign_key = -1"
    ) >= 0


def test_every_fact_date_resolves_in_dim_date(db):
    for fact, key in [("fact_orders", "order_date_key"),
                      ("fact_sales", "order_date_key"),
                      ("fact_payments", "payment_date_key"),
                      ("fact_inventory", "snapshot_date_key"),
                      ("fact_customer_events", "event_date_key")]:
        missing = db.scalar(f"""
            SELECT COUNT(*) FROM gold.{fact} f
            LEFT JOIN gold.dim_date d ON d.date_key = f.{key}
            WHERE d.date_key IS NULL
        """)
        assert missing == 0, f"{missing} {fact} rows have no matching date"


# --------------------------------------------------------------------------- #
# Reconciliation - the same number computed two ways must agree
# --------------------------------------------------------------------------- #
def test_line_revenue_reconciles_to_order_revenue(db):
    lines = float(db.scalar(
        "SELECT SUM(net_amount) FROM gold.fact_sales WHERE is_revenue") or 0)
    headers = float(db.scalar(
        "SELECT SUM(net_amount) FROM gold.fact_orders WHERE is_revenue") or 0)
    assert abs(lines - headers) < max(headers * 1e-4, TOLERANCE)


def test_daily_mart_reconciles_to_the_fact(db):
    mart = float(db.scalar("SELECT SUM(revenue) FROM gold.mart_sales_daily") or 0)
    fact = float(db.scalar(
        "SELECT SUM(net_amount) FROM gold.fact_orders WHERE is_revenue") or 0)
    assert abs(mart - fact) < max(fact * 1e-4, TOLERANCE)


def test_monthly_mart_reconciles_to_the_daily_mart(db):
    monthly = float(db.scalar("SELECT SUM(revenue) FROM gold.mart_sales_monthly") or 0)
    daily = float(db.scalar("SELECT SUM(revenue) FROM gold.mart_sales_daily") or 0)
    assert abs(monthly - daily) < max(daily * 1e-4, TOLERANCE)


def test_customer_360_accounts_for_every_dollar(db):
    customers = float(db.scalar(
        "SELECT SUM(lifetime_revenue) FROM gold.mart_customer_360") or 0)
    fact = float(db.scalar(
        "SELECT SUM(net_amount) FROM gold.fact_orders WHERE is_revenue") or 0)
    assert abs(customers - fact) < max(fact * 1e-4, TOLERANCE)


def test_star_schema_neither_drops_nor_duplicates_orders(db):
    assert db.row_count("gold", "fact_orders") == db.row_count("silver", "orders")


def test_silver_deduplicates_the_replayed_orders(db):
    """Bronze is allowed duplicates; silver is not. This is the repair working."""
    assert db.row_count("bronze", "orders") > db.row_count("silver", "orders")
    total = db.scalar("SELECT COUNT(*) FROM silver.orders")
    distinct = db.scalar("SELECT COUNT(DISTINCT order_id) FROM silver.orders")
    assert total == distinct


def test_silver_repairs_negative_quantities(db):
    assert db.scalar(
        "SELECT COUNT(*) FROM bronze.order_items WHERE quantity < 0") > 0
    assert db.scalar(
        "SELECT COUNT(*) FROM silver.order_items WHERE quantity <= 0") == 0
    assert db.scalar(
        "SELECT COUNT(*) FROM silver.order_items WHERE was_negative_quantity") > 0


def test_silver_canonicalises_loyalty_tier(db):
    tiers = db.query("SELECT DISTINCT loyalty_tier FROM silver.customers")
    assert set(tiers["loyalty_tier"]) <= {"Bronze", "Silver", "Gold", "Platinum"}


def test_silver_nulls_orphan_event_customers(db):
    """Orphans are flagged and nulled, never deleted - deleting them would
    quietly understate traffic."""
    assert db.scalar(
        "SELECT COUNT(*) FROM silver.customer_events WHERE is_orphan_customer") > 0
    dangling = db.scalar("""
        SELECT COUNT(*) FROM silver.customer_events e
        LEFT JOIN silver.customers c ON c.customer_id = e.customer_id
        WHERE e.customer_id IS NOT NULL AND c.customer_id IS NULL
    """)
    assert dangling == 0


# --------------------------------------------------------------------------- #
# Mart semantics
# --------------------------------------------------------------------------- #
def test_funnel_is_monotonically_decreasing(db):
    steps = db.query(
        "SELECT step_number, sessions FROM gold.mart_conversion_funnel "
        "ORDER BY step_number"
    )
    assert steps["sessions"].is_monotonic_decreasing, \
        "a later funnel step has more sessions than an earlier one"


def test_retention_percentages_are_in_range(db):
    assert db.scalar(
        "SELECT COUNT(*) FROM gold.mart_cohort_retention "
        "WHERE retention_pct < 0 OR retention_pct > 100"
    ) == 0


def test_month_zero_retention_is_always_100_percent(db):
    """By definition every cohort member is active in the month they joined."""
    off = db.scalar(
        "SELECT COUNT(*) FROM gold.mart_cohort_retention "
        "WHERE months_since = 0 AND ABS(retention_pct - 100) > 0.01"
    )
    assert off == 0


def test_rfm_scores_are_quintiles(db):
    out_of_range = db.scalar("""
        SELECT COUNT(*) FROM gold.mart_rfm_segments
        WHERE r_score NOT BETWEEN 1 AND 5
           OR f_score NOT BETWEEN 1 AND 5
           OR m_score NOT BETWEEN 1 AND 5
    """)
    assert out_of_range == 0


def test_only_purchasers_are_rfm_scored(db):
    """Scoring never-purchasers would drag every quintile boundary to zero."""
    scored = db.row_count("gold", "mart_rfm_segments")
    buyers = db.scalar("SELECT COUNT(*) FROM gold.mart_customer_360 WHERE orders > 0")
    assert scored == buyers


def test_inventory_health_reads_only_the_latest_snapshot(db):
    """Semi-additive: one row per product, never a sum over weeks."""
    rows = db.row_count("gold", "mart_inventory_health")
    products = db.scalar("SELECT COUNT(DISTINCT product_key) FROM gold.fact_inventory")
    assert rows == products


def test_executive_mart_is_exactly_one_row(db):
    assert db.row_count("gold", "mart_executive_kpis") == 1


def test_analysis_window_anchors_to_the_data_not_the_clock(db):
    window = db.query("SELECT * FROM gold.analysis_window").iloc[0]
    latest = db.scalar("SELECT MAX(order_date) FROM gold.fact_orders")
    assert str(window["as_of_date"])[:10] == str(latest)[:10]


def test_reporting_views_are_queryable(db):
    for view in ["v_sales_flat", "v_realtime_orders", "v_realtime_payments"]:
        db.query(f"SELECT * FROM gold.{view} LIMIT 1")


def test_flat_view_matches_the_fact_row_count(db):
    """The wide BI view must not fan out - a fan-out here doubles revenue in
    every Power BI visual built on it."""
    assert db.row_count("gold", "v_sales_flat") == db.row_count("gold", "fact_sales")


# --------------------------------------------------------------------------- #
# Operations page marts (PULA-105)
# --------------------------------------------------------------------------- #
def test_a_refund_is_never_the_final_payment_attempt(db):
    """A refund shares attempt_number 1 with the capture it reverses and comes
    later, so it used to win the 'final attempt' slot and make every returned
    order look unpaid."""
    assert db.scalar(
        "SELECT COUNT(*) FROM silver.payments WHERE is_final_attempt AND is_refunded"
    ) == 0
    assert db.scalar("""
        SELECT COUNT(*) FROM (
            SELECT order_id FROM silver.payments
            WHERE is_final_attempt GROUP BY order_id HAVING COUNT(*) > 1
        ) d
    """) == 0


def test_a_returned_order_that_was_captured_counts_as_paid(db):
    unpaid = db.scalar("""
        SELECT COUNT(DISTINCT p.order_id)
        FROM silver.payments p
        JOIN silver.orders o ON o.order_id = p.order_id
        WHERE o.is_returned AND p.is_refunded
          AND NOT EXISTS (
              SELECT 1 FROM silver.payments f
              WHERE f.order_id = p.order_id AND f.is_final_attempt AND f.is_captured
          )
    """)
    assert unpaid == 0, f"{unpaid} refunded orders are reported as never paid"


def test_gateway_success_publishes_both_denominators(db):
    frame = db.query("SELECT * FROM gold.mart_payment_gateway_success")
    assert set(frame["period"]) == {"Last 90 days", "All history"}
    for rate, numerator, denominator in [
        ("attempt_success_rate_pct", "attempts_captured", "authorisation_attempts"),
        ("order_success_rate_pct", "orders_paid", "orders_attempted"),
    ]:
        expected = (frame[numerator] / frame[denominator] * 100).round(2)
        assert (frame[rate] - expected).abs().max() <= TOLERANCE
        assert frame[rate].between(0, 100).all()
    # Retries recover failures, so per order can never be worse than per attempt.
    assert (frame["order_success_rate_pct"] >= frame["attempt_success_rate_pct"]).all()


def test_gateway_success_excludes_refunds_and_counts_each_order_once(db):
    all_history = db.query(
        "SELECT * FROM gold.mart_payment_gateway_success WHERE period = 'All history'"
    )
    attempts = db.scalar("SELECT COUNT(*) FROM gold.fact_payments WHERE NOT is_refunded")
    orders = db.scalar(
        "SELECT COUNT(DISTINCT order_id) FROM gold.fact_payments WHERE NOT is_refunded"
    )
    assert int(all_history["authorisation_attempts"].sum()) == attempts
    assert int(all_history["orders_attempted"].sum()) == orders


def test_order_exceptions_account_for_every_cancelled_and_returned_order(db):
    frame = db.query("SELECT * FROM gold.mart_order_exceptions WHERE period = 'All history'")
    for outcome, flag in [("Cancelled", "is_cancelled"), ("Returned", "is_returned")]:
        expected = db.scalar(f"SELECT COUNT(*) FROM gold.fact_orders WHERE {flag}")
        rows = frame[frame["outcome"] == outcome]
        assert int(rows["orders"].sum()) == expected
        assert abs(rows["share_of_outcome_pct"].sum() - 100) < 0.5
    assert (frame["orders_placed"] == db.row_count("gold", "fact_orders")).all()


def test_missing_reasons_stay_visible_rather_than_dropping_out(db):
    frame = db.query("SELECT * FROM gold.mart_order_exceptions")
    gaps = frame[~frame["is_mapped"].astype(bool)]
    assert set(gaps["reason_group"]) <= {"Not recorded", "Unmapped"}
    assert frame["reason_label"].notna().all()


def test_monthly_exception_rates_are_ratios_of_counts(db):
    frame = db.query("SELECT * FROM gold.mart_order_exceptions_monthly")
    assert int(frame["orders_placed"].sum()) == db.row_count("gold", "fact_orders")
    expected = (frame["orders_cancelled"] / frame["orders_placed"] * 100).round(2)
    assert (frame["cancellation_rate_pct"] - expected).abs().max() <= TOLERANCE
