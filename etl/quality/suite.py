"""The data-quality suite PulseAnalytics runs on every pipeline execution.

Read this file as the platform's contract with its consumers. Anything asserted
here is something a dashboard is allowed to rely on; anything not asserted here
is something nobody should be surprised by.

Thresholds are deliberately non-zero where the *source system is known to be
imperfect*. Setting them to zero would turn a known, quantified, accepted
business reality (a fraction of a percent of customers have no email address)
into a nightly false alarm - and a suite that cries wolf is a suite that gets
switched off.
"""
from __future__ import annotations

from etl.quality.checks import (
    Check,
    accepted_values,
    expression_holds,
    foreign_key,
    fresh_within_days,
    not_null,
    reconciles,
    row_count_at_least,
    unique,
)

ORDER_STATUSES = ["completed", "cancelled", "returned", "pending"]
PAYMENT_STATUSES = ["captured", "failed", "refunded"]
LOYALTY_TIERS = ["Bronze", "Silver", "Gold", "Platinum"]

# The analysis anchor, reused by every timeliness check.
AS_OF = "SELECT as_of_date FROM gold.analysis_window"


# --------------------------------------------------------------------------- #
# Bronze - "did the extract arrive intact"
# --------------------------------------------------------------------------- #
def bronze_checks() -> list[Check]:
    return [
        row_count_at_least("bronze", "orders", 1),
        row_count_at_least("bronze", "order_items", 1),
        row_count_at_least("bronze", "customers", 1),
        row_count_at_least("bronze", "products", 1),
        row_count_at_least("bronze", "payments", 1),

        not_null("bronze", "orders", "order_id"),
        not_null("bronze", "orders", "customer_id"),
        not_null("bronze", "orders", "order_ts"),
        not_null("bronze", "order_items", "order_id"),
        not_null("bronze", "customers", "customer_id"),
        not_null("bronze", "products", "product_id"),

        # Known and accepted: the CRM allows an account without an email.
        # Quantified at 2% so a real regression still trips it.
        not_null("bronze", "customers", "email", severity="warning", threshold_pct=2.0),

        # Known and accepted: the returns integration emits negative quantities.
        # Silver repairs them; bronze only has to notice.
        expression_holds(
            "order_items.quantity is positive", "bronze", "order_items",
            "quantity > 0", dimension="validity",
            severity="warning", threshold_pct=2.0,
            details="Negative quantities from the returns feed; repaired in silver.",
        ),

        # Bronze is allowed duplicate orders (the source replays them). Silver
        # is not - see silver_checks. Recorded here so the volume is visible.
        Check(
            name="orders.order_id duplicate rate", layer="bronze", table="orders",
            dimension="uniqueness", severity="warning", threshold_pct=2.0,
            failing_sql=(
                "SELECT COALESCE(SUM(n - 1), 0) AS failed_rows, COALESCE(SUM(n), 0) AS total_rows "
                "FROM (SELECT order_id, COUNT(*) AS n FROM bronze.orders GROUP BY order_id) d"
            ),
            details="Source system replays a small number of orders; de-duplicated in silver.",
        ),

        expression_holds(
            "orders.total_amount is not negative", "bronze", "orders",
            "COALESCE(total_amount, 0) >= 0", dimension="validity",
        ),
        expression_holds(
            "products.unit_cost below unit_price", "bronze", "products",
            "unit_cost < unit_price", dimension="validity",
            details="A product sold below cost would invert every margin metric.",
        ),
    ]


# --------------------------------------------------------------------------- #
# Silver - "did the cleaning actually work"
# --------------------------------------------------------------------------- #
def silver_checks() -> list[Check]:
    return [
        unique("silver", "orders", "order_id"),
        unique("silver", "order_items", "order_item_id"),
        unique("silver", "customers", "customer_id"),
        unique("silver", "products", "product_id"),
        unique("silver", "payments", "payment_id"),

        not_null("silver", "orders", "order_date"),
        not_null("silver", "orders", "status"),
        not_null("silver", "customers", "loyalty_tier"),

        accepted_values("silver", "orders", "status", ORDER_STATUSES),
        accepted_values("silver", "payments", "status", PAYMENT_STATUSES),
        accepted_values("silver", "customers", "loyalty_tier", LOYALTY_TIERS),

        # The repairs promised by the silver layer, asserted rather than assumed.
        expression_holds(
            "order_items.quantity repaired to positive", "silver", "order_items",
            "quantity > 0", dimension="validity",
            details="Silver must have taken the absolute value of every negative quantity.",
        ),
        expression_holds(
            "customers.loyalty_tier is canonicalised", "silver", "customers",
            "loyalty_tier = TRIM(loyalty_tier) AND loyalty_tier <> UPPER(loyalty_tier)",
            dimension="validity",
            details="'GOLD  ' and 'gold' must both have become 'Gold'.",
        ),
        expression_holds(
            "orders.net_amount is consistent", "silver", "orders",
            "ABS(net_amount - (gross_amount - discount_amount)) < 0.05",
            dimension="accuracy",
            details="Header totals must equal the sum of their lines.",
        ),

        # Referential integrity across the cleaned model.
        foreign_key("silver", "orders", "customer_id", "silver", "customers", "customer_id"),
        foreign_key("silver", "orders", "store_id", "silver", "stores", "store_id"),
        foreign_key("silver", "order_items", "order_id", "silver", "orders", "order_id"),
        foreign_key("silver", "order_items", "product_id", "silver", "products", "product_id"),
        foreign_key("silver", "payments", "order_id", "silver", "orders", "order_id"),
        # Orphan event customers are nulled by silver, so this must now be clean.
        foreign_key("silver", "customer_events", "customer_id",
                    "silver", "customers", "customer_id"),

        expression_holds(
            "orders are inside the two-year window", "silver", "orders",
            "order_date >= DATE '2022-01-01' AND order_date <= DATE '2027-12-31'",
            dimension="validity",
            details="Guards against a timezone or epoch bug shifting dates wholesale.",
        ),
        # Temporal consistency across two tables: an order cannot exist before
        # the customer who placed it.
        Check(
            name="no order predates its customer's signup",
            layer="silver", table="orders", dimension="consistency",
            severity="warning", threshold_pct=0.5,
            failing_sql=(
                "SELECT COUNT(*) FILTER (WHERE o.order_date < c.signup_date) AS failed_rows, "
                "COUNT(*) AS total_rows "
                "FROM silver.orders o JOIN silver.customers c ON c.customer_id = o.customer_id"
            ),
            details="Backdated orders indicate a customer-master sync problem.",
        ),
        Check(
            name="no order line predates its product launch",
            layer="silver", table="order_items", dimension="consistency",
            severity="warning", threshold_pct=0.5,
            failing_sql=(
                "SELECT COUNT(*) FILTER (WHERE o.order_date < p.launch_date) AS failed_rows, "
                "COUNT(*) AS total_rows "
                "FROM silver.order_items oi "
                "JOIN silver.orders o   ON o.order_id = oi.order_id "
                "JOIN silver.products p ON p.product_id = oi.product_id"
            ),
            details="Selling a product before it launched means a bad catalogue join.",
        ),
    ]


# --------------------------------------------------------------------------- #
# Gold - "is the warehouse safe to publish"
# --------------------------------------------------------------------------- #
def gold_checks() -> list[Check]:
    return [
        row_count_at_least("gold", "fact_sales", 1),
        row_count_at_least("gold", "fact_orders", 1),
        row_count_at_least("gold", "dim_customer", 2),
        row_count_at_least("gold", "mart_executive_kpis", 1),

        unique("gold", "dim_customer", "customer_key"),
        unique("gold", "dim_product", "product_key"),
        unique("gold", "dim_date", "date_key"),
        unique("gold", "fact_orders", "order_key"),
        unique("gold", "fact_sales", "sales_key"),

        # No fact row may point at the Unknown member: that would mean a join
        # silently failed and revenue is being attributed to nobody.
        expression_holds(
            "fact_sales has no unknown customer", "gold", "fact_sales",
            "customer_key <> -1", dimension="consistency",
        ),
        expression_holds(
            "fact_sales has no unknown product", "gold", "fact_sales",
            "product_key <> -1", dimension="consistency",
        ),
        expression_holds(
            "fact_orders has no unknown store", "gold", "fact_orders",
            "store_key <> -1", dimension="consistency",
        ),

        expression_holds(
            "fact_sales margin is plausible", "gold", "fact_sales",
            "margin_pct BETWEEN -100 AND 100", dimension="validity",
        ),
        expression_holds(
            "fact_orders revenue is not negative", "gold", "fact_orders",
            "net_amount >= 0", dimension="validity",
        ),

        # ---- accuracy: the same number computed two different ways ----------
        reconciles(
            "line revenue reconciles to order revenue", "gold", "fact_sales",
            """
            SELECT
                (SELECT SUM(net_amount) FROM gold.fact_sales  WHERE is_revenue) AS left_value,
                (SELECT SUM(net_amount) FROM gold.fact_orders WHERE is_revenue) AS right_value
            """,
            details="Order-line grain and order-header grain must agree on revenue.",
        ),
        reconciles(
            "daily mart reconciles to fact_orders", "gold", "mart_sales_daily",
            """
            SELECT
                (SELECT SUM(revenue) FROM gold.mart_sales_daily) AS left_value,
                (SELECT SUM(net_amount) FROM gold.fact_orders WHERE is_revenue) AS right_value
            """,
            details="The aggregate mart must not drift from the fact it is built on.",
        ),
        reconciles(
            "monthly mart reconciles to daily mart", "gold", "mart_sales_monthly",
            """
            SELECT
                (SELECT SUM(revenue) FROM gold.mart_sales_monthly) AS left_value,
                (SELECT SUM(revenue) FROM gold.mart_sales_daily)   AS right_value
            """,
        ),
        reconciles(
            "customer 360 reconciles to fact_orders", "gold", "mart_customer_360",
            """
            SELECT
                (SELECT SUM(lifetime_revenue) FROM gold.mart_customer_360) AS left_value,
                (SELECT SUM(net_amount) FROM gold.fact_orders WHERE is_revenue) AS right_value
            """,
            details="Every dollar of revenue must belong to exactly one customer.",
        ),
        reconciles(
            "silver orders survive into fact_orders", "gold", "fact_orders",
            """
            SELECT
                (SELECT COUNT(*) FROM gold.fact_orders)  AS left_value,
                (SELECT COUNT(*) FROM silver.orders)     AS right_value
            """,
            details="The star schema must not drop or duplicate orders.",
        ),

        # ---- funnel sanity --------------------------------------------------
        expression_holds(
            "funnel is monotonically decreasing", "gold", "mart_conversion_funnel",
            "prev_step_sessions IS NULL OR sessions <= prev_step_sessions",
            dimension="consistency",
            details="A later funnel step can never have more sessions than an earlier one.",
        ),
        expression_holds(
            "retention percentages are in range", "gold", "mart_cohort_retention",
            "retention_pct BETWEEN 0 AND 100", dimension="validity",
        ),
        expression_holds(
            "RFM scores are 1-5", "gold", "mart_rfm_segments",
            "r_score BETWEEN 1 AND 5 AND f_score BETWEEN 1 AND 5 AND m_score BETWEEN 1 AND 5",
            dimension="validity",
        ),

        # ---- timeliness -----------------------------------------------------
        fresh_within_days("gold", "fact_orders", "order_date", 2, AS_OF),
        fresh_within_days("gold", "fact_customer_events", "event_date", 7, AS_OF),
        fresh_within_days("gold", "fact_inventory", "snapshot_date", 14, AS_OF),
    ]


def full_suite() -> list[Check]:
    return bronze_checks() + silver_checks() + gold_checks()


SUITES = {
    "bronze": bronze_checks,
    "silver": silver_checks,
    "gold": gold_checks,
    "all": full_suite,
}
