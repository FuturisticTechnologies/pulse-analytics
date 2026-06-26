-- ===========================================================================
-- gold.mart_executive_kpis - the single row the executive dashboard reads.
--
-- One row, one column per headline KPI, each with its trailing-90-day value,
-- the preceding 90 days, and the percentage change. Computing it once here
-- (rather than eleven times in the BI tool) is what stops two dashboards from
-- quoting two different revenue numbers in the same meeting.
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_executive_kpis;
CREATE TABLE gold.mart_executive_kpis AS
WITH win AS (
    SELECT * FROM gold.analysis_window
),
cur AS (
    SELECT
        COUNT(*)                                            AS orders,
        COUNT(DISTINCT o.customer_key)                      AS active_customers,
        COUNT(*) FILTER (WHERE o.is_first_order)            AS new_customers,
        SUM(o.item_count)                                   AS units,
        ROUND(SUM(o.net_amount), 2)                         AS revenue,
        ROUND(SUM(o.gross_profit), 2)                       AS gross_profit,
        ROUND(SUM(o.discount_amount), 2)                    AS discounts
    FROM gold.fact_orders o
    CROSS JOIN win w
    WHERE o.is_revenue AND o.order_date >= w.trailing_90_start
),
prev AS (
    SELECT
        COUNT(*)                                            AS orders,
        COUNT(DISTINCT o.customer_key)                      AS active_customers,
        COUNT(*) FILTER (WHERE o.is_first_order)            AS new_customers,
        ROUND(SUM(o.net_amount), 2)                         AS revenue,
        ROUND(SUM(o.gross_profit), 2)                       AS gross_profit
    FROM gold.fact_orders o
    CROSS JOIN win w
    WHERE o.is_revenue
      AND o.order_date >= w.trailing_90_start - 90
      AND o.order_date <  w.trailing_90_start
),
lifetime AS (
    SELECT
        COUNT(*)                                            AS orders_all_time,
        ROUND(SUM(net_amount), 2)                           AS revenue_all_time,
        ROUND(SUM(gross_profit), 2)                         AS gross_profit_all_time
    FROM gold.fact_orders WHERE is_revenue
),
customers AS (
    SELECT
        COUNT(*)                                            AS customers_total,
        COUNT(*) FILTER (WHERE orders > 0)                  AS customers_ever_ordered,
        COUNT(*) FILTER (WHERE is_repeat_buyer)             AS repeat_customers,
        COUNT(*) FILTER (WHERE lifecycle_status = 'Active') AS active_customers_total,
        COUNT(*) FILTER (WHERE lifecycle_status = 'At Risk') AS at_risk_customers,
        COUNT(*) FILTER (WHERE is_churned)                  AS churned_customers,
        ROUND(AVG(lifetime_revenue) FILTER (WHERE orders > 0), 2) AS avg_lifetime_revenue
    FROM gold.mart_customer_360
),
marketing AS (
    SELECT
        ROUND(SUM(spend), 2)                                AS marketing_spend,
        ROUND(SUM(revenue), 2)                              AS marketing_revenue,
        SUM(new_customers)                                  AS marketing_new_customers
    FROM gold.mart_campaign_performance
),
payments AS (
    SELECT
        SUM(attempts)                                       AS payment_attempts,
        SUM(failed)                                         AS payment_failures,
        ROUND(SUM(failed_amount), 2)                        AS payment_amount_at_risk
    FROM gold.mart_payment_health p
    CROSS JOIN win w
    WHERE p.payment_date >= w.trailing_90_start
),
inventory AS (
    SELECT
        COUNT(*)                                            AS products_tracked,
        COUNT(*) FILTER (WHERE is_stockout)                 AS products_stocked_out,
        COUNT(*) FILTER (WHERE is_below_reorder)            AS products_below_reorder,
        ROUND(SUM(on_hand_value_at_cost), 2)                AS stock_value_at_cost
    FROM gold.mart_inventory_health
)
SELECT
    w.as_of_date,
    w.trailing_90_start                                     AS period_start,
    -- ---- headline trading -------------------------------------------------
    cur.revenue                                             AS revenue_90d,
    prev.revenue                                            AS revenue_prev_90d,
    CASE WHEN prev.revenue > 0
         THEN ROUND((cur.revenue - prev.revenue) / prev.revenue * 100, 2) END AS revenue_change_pct,
    cur.gross_profit                                        AS gross_profit_90d,
    CASE WHEN cur.revenue > 0
         THEN ROUND(cur.gross_profit / cur.revenue * 100, 2) END              AS gross_margin_pct,
    cur.orders                                              AS orders_90d,
    prev.orders                                             AS orders_prev_90d,
    CASE WHEN prev.orders > 0
         THEN ROUND(CAST(cur.orders - prev.orders AS DOUBLE PRECISION) / prev.orders * 100, 2) END
                                                            AS orders_change_pct,
    CASE WHEN cur.orders > 0 THEN ROUND(cur.revenue / cur.orders, 2) END      AS avg_order_value,
    CASE WHEN prev.orders > 0 THEN ROUND(prev.revenue / prev.orders, 2) END   AS avg_order_value_prev,
    cur.units                                               AS units_90d,
    cur.discounts                                           AS discounts_90d,
    -- ---- customers --------------------------------------------------------
    cur.active_customers                                    AS active_customers_90d,
    cur.new_customers                                       AS new_customers_90d,
    CASE WHEN prev.new_customers > 0
         THEN ROUND(CAST(cur.new_customers - prev.new_customers AS DOUBLE PRECISION)
                    / prev.new_customers * 100, 2) END      AS new_customers_change_pct,
    c.customers_total,
    c.customers_ever_ordered,
    c.repeat_customers,
    ROUND(CAST(c.repeat_customers AS DOUBLE PRECISION)
          / NULLIF(c.customers_ever_ordered, 0) * 100, 2)   AS repeat_rate_pct,
    c.active_customers_total,
    c.at_risk_customers,
    c.churned_customers,
    ROUND(CAST(c.churned_customers AS DOUBLE PRECISION)
          / NULLIF(c.customers_ever_ordered, 0) * 100, 2)   AS churn_rate_pct,
    c.avg_lifetime_revenue,
    -- ---- marketing --------------------------------------------------------
    m.marketing_spend,
    m.marketing_revenue,
    CASE WHEN m.marketing_spend > 0
         THEN ROUND(m.marketing_revenue / m.marketing_spend, 2) END           AS blended_roas,
    CASE WHEN m.marketing_new_customers > 0
         THEN ROUND(m.marketing_spend / m.marketing_new_customers, 2) END     AS blended_cac,
    -- ---- operations -------------------------------------------------------
    p.payment_attempts,
    p.payment_failures,
    ROUND(CAST(p.payment_failures AS DOUBLE PRECISION)
          / NULLIF(p.payment_attempts, 0) * 100, 2)         AS payment_failure_rate_pct,
    p.payment_amount_at_risk,
    i.products_tracked,
    i.products_stocked_out,
    i.products_below_reorder,
    i.stock_value_at_cost,
    -- ---- all time ---------------------------------------------------------
    lt.orders_all_time,
    lt.revenue_all_time,
    lt.gross_profit_all_time
FROM win w
CROSS JOIN cur
CROSS JOIN prev
CROSS JOIN lifetime lt
CROSS JOIN customers c
CROSS JOIN marketing m
CROSS JOIN payments p
CROSS JOIN inventory i;
