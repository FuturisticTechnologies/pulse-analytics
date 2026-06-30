-- ===========================================================================
-- Regional and store performance.
--
-- Same measures at two grains so a regional director and a store manager read
-- the same definitions. Store productivity uses revenue per square metre for
-- physical stores only - applying it to an online store would produce an
-- infinite number, which is exactly the sort of thing that destroys trust in a
-- dashboard, so it is NULL by construction.
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_regional_performance;
CREATE TABLE gold.mart_regional_performance AS
WITH win AS (
    SELECT * FROM gold.analysis_window
),
by_region AS (
    SELECT
        o.region_key,
        COUNT(*)                                                AS orders,
        COUNT(DISTINCT o.customer_key)                          AS customers,
        COUNT(*) FILTER (WHERE o.is_first_order)                AS new_customers,
        SUM(o.item_count)                                       AS units,
        ROUND(SUM(o.net_amount), 2)                             AS revenue,
        ROUND(SUM(o.gross_profit), 2)                           AS gross_profit,
        ROUND(SUM(o.discount_amount), 2)                        AS discounts,
        ROUND(AVG(o.net_amount), 2)                             AS avg_order_value
    FROM gold.fact_orders o
    WHERE o.is_revenue
    GROUP BY o.region_key
),
recent_region AS (
    SELECT
        o.region_key,
        ROUND(SUM(o.net_amount), 2)                             AS revenue_90d
    FROM gold.fact_orders o
    CROSS JOIN win w
    WHERE o.is_revenue AND o.order_date >= w.trailing_90_start
    GROUP BY o.region_key
),
prior_region AS (
    SELECT
        o.region_key,
        ROUND(SUM(o.net_amount), 2)                             AS revenue_prev_90d
    FROM gold.fact_orders o
    CROSS JOIN win w
    WHERE o.is_revenue
      AND o.order_date >= w.trailing_90_start - 90
      AND o.order_date <  w.trailing_90_start
    GROUP BY o.region_key
)
SELECT
    r.region_key,
    r.region_id,
    r.region_name,
    r.country,
    r.super_region,
    COALESCE(b.orders, 0)                                       AS orders,
    COALESCE(b.customers, 0)                                    AS customers,
    COALESCE(b.new_customers, 0)                                AS new_customers,
    COALESCE(b.units, 0)                                        AS units,
    COALESCE(b.revenue, 0)                                      AS revenue,
    COALESCE(b.gross_profit, 0)                                 AS gross_profit,
    COALESCE(b.discounts, 0)                                    AS discounts,
    COALESCE(b.avg_order_value, 0)                              AS avg_order_value,
    COALESCE(rr.revenue_90d, 0)                                 AS revenue_90d,
    COALESCE(pr.revenue_prev_90d, 0)                            AS revenue_prev_90d,
    CASE WHEN COALESCE(pr.revenue_prev_90d, 0) > 0
         THEN ROUND((COALESCE(rr.revenue_90d, 0) - pr.revenue_prev_90d)
                    / pr.revenue_prev_90d * 100, 2)
         ELSE NULL END                                          AS revenue_trend_pct,
    CASE WHEN COALESCE(b.revenue, 0) > 0
         THEN ROUND(b.gross_profit / b.revenue * 100, 2) ELSE 0 END AS gross_margin_pct,
    CASE WHEN COALESCE(b.customers, 0) > 0
         THEN ROUND(b.revenue / b.customers, 2) ELSE 0 END      AS revenue_per_customer,
    ROUND(COALESCE(b.revenue, 0)
          / NULLIF(SUM(COALESCE(b.revenue, 0)) OVER (), 0) * 100, 2) AS revenue_share_pct,
    CAST(RANK() OVER (ORDER BY COALESCE(b.revenue, 0) DESC) AS INTEGER) AS revenue_rank
FROM gold.dim_region r
LEFT JOIN by_region     b  ON b.region_key  = r.region_key
LEFT JOIN recent_region rr ON rr.region_key = r.region_key
LEFT JOIN prior_region  pr ON pr.region_key = r.region_key
WHERE r.region_key <> -1;

-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.mart_store_performance;
CREATE TABLE gold.mart_store_performance AS
WITH by_store AS (
    SELECT
        o.store_key,
        COUNT(*)                                                AS orders,
        COUNT(DISTINCT o.customer_key)                          AS customers,
        SUM(o.item_count)                                       AS units,
        ROUND(SUM(o.net_amount), 2)                             AS revenue,
        ROUND(SUM(o.gross_profit), 2)                           AS gross_profit,
        ROUND(AVG(o.net_amount), 2)                             AS avg_order_value,
        MIN(o.order_date)                                       AS first_order_date,
        MAX(o.order_date)                                       AS last_order_date
    FROM gold.fact_orders o
    WHERE o.is_revenue
    GROUP BY o.store_key
)
SELECT
    s.store_key,
    s.store_id,
    s.store_name,
    s.store_type,
    s.city,
    s.country,
    s.is_digital,
    s.floor_sqm,
    s.opened_date,
    COALESCE(b.orders, 0)                                       AS orders,
    COALESCE(b.customers, 0)                                    AS customers,
    COALESCE(b.units, 0)                                        AS units,
    COALESCE(b.revenue, 0)                                      AS revenue,
    COALESCE(b.gross_profit, 0)                                 AS gross_profit,
    COALESCE(b.avg_order_value, 0)                              AS avg_order_value,
    CASE WHEN COALESCE(b.revenue, 0) > 0
         THEN ROUND(b.gross_profit / b.revenue * 100, 2) ELSE 0 END AS gross_margin_pct,
    -- Only meaningful for physical space.
    CASE WHEN s.is_digital OR COALESCE(s.floor_sqm, 0) <= 0 THEN NULL
         ELSE ROUND(COALESCE(b.revenue, 0) / s.floor_sqm, 2) END AS revenue_per_sqm,
    b.first_order_date,
    b.last_order_date,
    CAST(RANK() OVER (ORDER BY COALESCE(b.revenue, 0) DESC) AS INTEGER) AS revenue_rank
FROM gold.dim_store s
LEFT JOIN by_store b ON b.store_key = s.store_key
WHERE s.store_key <> -1;

-- ---------------------------------------------------------------------------
-- gold.mart_category_performance - the merchandising planning grid.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.mart_category_performance;
CREATE TABLE gold.mart_category_performance AS
SELECT
    p.category,
    p.subcategory,
    COUNT(DISTINCT p.product_key)                               AS products,
    COUNT(DISTINCT s.order_id)                                  AS orders,
    SUM(s.quantity)                                             AS units,
    ROUND(SUM(s.net_amount), 2)                                 AS revenue,
    ROUND(SUM(s.gross_profit), 2)                               AS gross_profit,
    ROUND(SUM(s.discount_amount), 2)                            AS discounts,
    CASE WHEN SUM(s.net_amount) > 0
         THEN ROUND(SUM(s.gross_profit) / SUM(s.net_amount) * 100, 2) ELSE 0 END AS gross_margin_pct,
    ROUND(SUM(s.net_amount) / NULLIF(SUM(SUM(s.net_amount)) OVER (), 0) * 100, 2) AS revenue_share_pct,
    ROUND(AVG(s.unit_price), 2)                                 AS avg_unit_price,
    COUNT(DISTINCT s.customer_key)                              AS buyers
FROM gold.fact_sales s
JOIN gold.dim_product p ON p.product_key = s.product_key
WHERE s.is_revenue AND p.product_key <> -1
GROUP BY p.category, p.subcategory;
