-- ===========================================================================
-- gold.mart_sales_daily - one row per calendar day.
--
-- The trading heartbeat. Carries the raw measures plus the comparisons every
-- daily review asks for: 7-day moving average (kills weekday noise), prior-day
-- and prior-year deltas, and a running month-to-date total.
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_sales_daily;
CREATE TABLE gold.mart_sales_daily AS
WITH daily AS (
    SELECT
        o.order_date,
        d.date_key,
        d.year_number,
        d.month_number,
        d.month_start,
        d.day_short,
        d.is_weekend,
        d.is_peak_season,
        COUNT(*)                                                        AS orders_placed,
        COUNT(*) FILTER (WHERE o.is_revenue)                            AS orders_completed,
        COUNT(*) FILTER (WHERE o.is_cancelled)                          AS orders_cancelled,
        COUNT(*) FILTER (WHERE o.is_returned)                           AS orders_returned,
        COUNT(DISTINCT o.customer_key)                                  AS active_customers,
        COUNT(DISTINCT o.customer_key) FILTER (WHERE o.is_first_order)  AS new_customers,
        SUM(o.item_count)  FILTER (WHERE o.is_revenue)                  AS units_sold,
        ROUND(SUM(o.net_amount)    FILTER (WHERE o.is_revenue), 2)      AS revenue,
        ROUND(SUM(o.gross_amount)  FILTER (WHERE o.is_revenue), 2)      AS gross_revenue,
        ROUND(SUM(o.discount_amount) FILTER (WHERE o.is_revenue), 2)    AS discounts,
        ROUND(SUM(o.cost_amount)   FILTER (WHERE o.is_revenue), 2)      AS cogs,
        ROUND(SUM(o.gross_profit)  FILTER (WHERE o.is_revenue), 2)      AS gross_profit,
        ROUND(SUM(o.shipping_amount) FILTER (WHERE o.is_revenue), 2)    AS shipping,
        ROUND(SUM(o.tax_amount)    FILTER (WHERE o.is_revenue), 2)      AS tax
    FROM gold.fact_orders o
    JOIN gold.dim_date d ON d.date_key = o.order_date_key
    GROUP BY o.order_date, d.date_key, d.year_number, d.month_number,
             d.month_start, d.day_short, d.is_weekend, d.is_peak_season
)
SELECT
    date_key,
    order_date,
    year_number,
    month_number,
    month_start,
    day_short,
    is_weekend,
    is_peak_season,
    orders_placed,
    orders_completed,
    orders_cancelled,
    orders_returned,
    active_customers,
    new_customers,
    COALESCE(units_sold, 0)                                             AS units_sold,
    COALESCE(revenue, 0)                                                AS revenue,
    COALESCE(gross_revenue, 0)                                          AS gross_revenue,
    COALESCE(discounts, 0)                                              AS discounts,
    COALESCE(cogs, 0)                                                   AS cogs,
    COALESCE(gross_profit, 0)                                           AS gross_profit,
    COALESCE(shipping, 0)                                               AS shipping,
    COALESCE(tax, 0)                                                    AS tax,
    CASE WHEN orders_completed > 0
         THEN ROUND(COALESCE(revenue, 0) / units_sold, 2) ELSE 0 END             AS avg_order_value,
    CASE WHEN COALESCE(revenue, 0) > 0
         THEN ROUND(COALESCE(gross_profit, 0) / revenue * 100, 2) ELSE 0 END     AS gross_margin_pct,
    CASE WHEN orders_placed > 0
         THEN ROUND(CAST(orders_cancelled AS DOUBLE PRECISION) / orders_placed * 100, 2)
         ELSE 0 END                                                              AS cancellation_rate_pct,
    -- 7-day moving average: the number an operator should actually react to.
    ROUND(AVG(COALESCE(revenue, 0)) OVER (
        ORDER BY order_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2)        AS revenue_ma7,
    ROUND(AVG(COALESCE(revenue, 0)) OVER (
        ORDER BY order_date ROWS BETWEEN 27 PRECEDING AND CURRENT ROW), 2)       AS revenue_ma28,
    ROUND(COALESCE(revenue, 0)
          - LAG(COALESCE(revenue, 0), 1) OVER (ORDER BY order_date), 2)          AS revenue_vs_prev_day,
    ROUND(COALESCE(revenue, 0)
          - LAG(COALESCE(revenue, 0), 7) OVER (ORDER BY order_date), 2)          AS revenue_vs_prev_week,
    ROUND(SUM(COALESCE(revenue, 0)) OVER (
        PARTITION BY month_start ORDER BY order_date), 2)                        AS revenue_mtd,
    ROUND(SUM(COALESCE(revenue, 0)) OVER (
        PARTITION BY year_number ORDER BY order_date), 2)                        AS revenue_ytd
FROM daily;
