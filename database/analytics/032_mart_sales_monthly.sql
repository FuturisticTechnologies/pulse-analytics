-- ===========================================================================
-- gold.mart_sales_monthly - one row per month, with MoM and YoY.
--
-- Monthly is the grain executives sign off on, and the grain where YoY is
-- meaningful across a two-year history. YoY uses LAG(12) over a dense month
-- series so a month with zero trading does not silently shift the comparison.
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_sales_monthly;
CREATE TABLE gold.mart_sales_monthly AS
WITH monthly AS (
    SELECT
        month_start,
        year_number,
        month_number,
        SUM(orders_completed)                       AS orders,
        SUM(orders_cancelled)                       AS orders_cancelled,
        SUM(orders_returned)                        AS orders_returned,
        SUM(units_sold)                             AS units_sold,
        SUM(new_customers)                          AS new_customers,
        ROUND(SUM(revenue), 2)                      AS revenue,
        ROUND(SUM(discounts), 2)                    AS discounts,
        ROUND(SUM(cogs), 2)                         AS cogs,
        ROUND(SUM(gross_profit), 2)                 AS gross_profit,
        COUNT(*)                                    AS trading_days
    FROM gold.mart_sales_daily
    GROUP BY month_start, year_number, month_number
), distinct_customers AS (
    SELECT
        CAST(DATE_TRUNC('month', CAST(order_date AS TIMESTAMP)) AS DATE) AS month_start,
        COUNT(DISTINCT customer_key)                AS active_customers
    FROM gold.fact_orders
    WHERE is_revenue
    GROUP BY 1
)
SELECT
    m.month_start,
    m.year_number,
    m.month_number,
    m.trading_days,
    m.orders,
    m.orders_cancelled,
    m.orders_returned,
    m.units_sold,
    m.new_customers,
    COALESCE(dc.active_customers, 0)                                  AS active_customers,
    m.revenue,
    m.discounts,
    m.cogs,
    m.gross_profit,
    CASE WHEN m.orders > 0 THEN ROUND(m.revenue / m.orders, 2) ELSE 0 END       AS avg_order_value,
    CASE WHEN m.revenue > 0 THEN ROUND(m.gross_profit / m.revenue * 100, 2) ELSE 0 END AS gross_margin_pct,
    CASE WHEN COALESCE(dc.active_customers, 0) > 0
         THEN ROUND(m.revenue / dc.active_customers, 2) ELSE 0 END              AS revenue_per_customer,
    CASE WHEN m.revenue > 0 THEN ROUND(m.discounts / (m.revenue + m.discounts) * 100, 2)
         ELSE 0 END                                                             AS discount_rate_pct,
    LAG(m.revenue, 1)  OVER (ORDER BY m.month_start)                            AS revenue_prev_month,
    LAG(m.revenue, 12) OVER (ORDER BY m.month_start)                            AS revenue_prev_year,
    CASE WHEN LAG(m.revenue, 1) OVER (ORDER BY m.month_start) > 0
         THEN ROUND((m.revenue - LAG(m.revenue, 1) OVER (ORDER BY m.month_start))
                    / LAG(m.revenue, 1) OVER (ORDER BY m.month_start) * 100, 2)
         ELSE NULL END                                                          AS revenue_mom_pct,
    CASE WHEN LAG(m.revenue, 12) OVER (ORDER BY m.month_start) > 0
         THEN ROUND((m.revenue - LAG(m.revenue, 12) OVER (ORDER BY m.month_start))
                    / LAG(m.revenue, 12) OVER (ORDER BY m.month_start) * 100, 2)
         ELSE NULL END                                                          AS revenue_yoy_pct,
    ROUND(SUM(m.revenue) OVER (ORDER BY m.month_start), 2)                      AS revenue_cumulative
FROM monthly m
LEFT JOIN distinct_customers dc ON dc.month_start = m.month_start;
