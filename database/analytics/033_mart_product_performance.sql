-- ===========================================================================
-- gold.mart_product_performance - one row per product, lifetime + trailing 90d.
--
-- Answers the merchandising questions: what earns, what only moves on
-- discount, what is a margin trap. The ABC class is a genuine Pareto (running
-- share of revenue), not a fixed top-N, so it adapts as the catalogue changes.
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_product_performance;
CREATE TABLE gold.mart_product_performance AS
WITH win AS (
    SELECT * FROM gold.analysis_window
),
lifetime AS (
    SELECT
        s.product_key,
        COUNT(DISTINCT s.order_id)                          AS orders,
        SUM(s.quantity)                                     AS units_sold,
        ROUND(SUM(s.net_amount), 2)                         AS revenue,
        ROUND(SUM(s.discount_amount), 2)                    AS discounts,
        ROUND(SUM(s.cost_amount), 2)                        AS cogs,
        ROUND(SUM(s.gross_profit), 2)                       AS gross_profit,
        COUNT(DISTINCT s.customer_key)                      AS buyers,
        MIN(s.order_date)                                   AS first_sold_date,
        MAX(s.order_date)                                   AS last_sold_date
    FROM gold.fact_sales s
    WHERE s.is_revenue
    GROUP BY s.product_key
),
returns AS (
    SELECT s.product_key, SUM(s.quantity) AS units_returned
    FROM gold.fact_sales s
    WHERE s.is_returned
    GROUP BY s.product_key
),
recent AS (
    SELECT
        s.product_key,
        SUM(s.quantity)                                     AS units_90d,
        ROUND(SUM(s.net_amount), 2)                         AS revenue_90d,
        ROUND(SUM(s.gross_profit), 2)                       AS gross_profit_90d
    FROM gold.fact_sales s
    CROSS JOIN win w
    WHERE s.is_revenue AND s.order_date >= w.trailing_90_start
    GROUP BY s.product_key
),
prior AS (
    SELECT
        s.product_key,
        ROUND(SUM(s.net_amount), 2)                         AS revenue_prev_90d
    FROM gold.fact_sales s
    CROSS JOIN win w
    WHERE s.is_revenue
      AND s.order_date >= w.trailing_90_start - 90
      AND s.order_date <  w.trailing_90_start
    GROUP BY s.product_key
),
joined AS (
    SELECT
        p.product_key,
        p.product_id,
        p.sku,
        p.product_name,
        p.category,
        p.subcategory,
        p.brand,
        p.price_band,
        p.unit_price,
        p.unit_cost,
        p.launch_date,
        p.is_active,
        COALESCE(l.orders, 0)                               AS orders,
        COALESCE(l.units_sold, 0)                           AS units_sold,
        COALESCE(l.buyers, 0)                               AS buyers,
        COALESCE(l.revenue, 0)                              AS revenue,
        COALESCE(l.discounts, 0)                            AS discounts,
        COALESCE(l.cogs, 0)                                 AS cogs,
        COALESCE(l.gross_profit, 0)                         AS gross_profit,
        COALESCE(rt.units_returned, 0)                      AS units_returned,
        l.first_sold_date,
        l.last_sold_date,
        COALESCE(r.units_90d, 0)                            AS units_90d,
        COALESCE(r.revenue_90d, 0)                          AS revenue_90d,
        COALESCE(r.gross_profit_90d, 0)                     AS gross_profit_90d,
        COALESCE(pr.revenue_prev_90d, 0)                    AS revenue_prev_90d
    FROM gold.dim_product p
    LEFT JOIN lifetime l  ON l.product_key  = p.product_key
    LEFT JOIN returns  rt ON rt.product_key = p.product_key
    LEFT JOIN recent   r  ON r.product_key  = p.product_key
    LEFT JOIN prior    pr ON pr.product_key = p.product_key
    WHERE p.product_key <> -1
),
ranked AS (
    SELECT
        j.*,
        CASE WHEN j.revenue > 0
             THEN ROUND(j.gross_profit / j.revenue * 100, 2) ELSE 0 END        AS margin_pct,
        CASE WHEN (j.revenue + j.discounts) > 0
             THEN ROUND(j.discounts / (j.revenue + j.discounts) * 100, 2)
             ELSE 0 END                                                        AS discount_rate_pct,
        CASE WHEN j.units_sold > 0
             THEN ROUND(CAST(j.units_returned AS DOUBLE PRECISION) / j.units_sold * 100, 2)
             ELSE 0 END                                                        AS return_rate_pct,
        CASE WHEN j.revenue_prev_90d > 0
             THEN ROUND((j.revenue_90d - j.revenue_prev_90d) / j.revenue_prev_90d * 100, 2)
             ELSE NULL END                                                     AS revenue_trend_pct,
        CAST(RANK() OVER (ORDER BY j.revenue DESC) AS INTEGER)                 AS revenue_rank,
        CAST(RANK() OVER (ORDER BY j.gross_profit DESC) AS INTEGER)            AS profit_rank,
        CAST(RANK() OVER (PARTITION BY j.category ORDER BY j.revenue DESC) AS INTEGER)
                                                                               AS rank_in_category,
        -- Running share of total revenue -> genuine ABC (Pareto) classification.
        SUM(j.revenue) OVER (ORDER BY j.revenue DESC
                             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
            / NULLIF(SUM(j.revenue) OVER (), 0)                                AS cumulative_revenue_share
    FROM joined j
)
SELECT
    r.*,
    CASE
        WHEN r.cumulative_revenue_share <= 0.80 THEN 'A'
        WHEN r.cumulative_revenue_share <= 0.95 THEN 'B'
        ELSE 'C'
    END                                                                        AS abc_class,
    -- Merchandising verdict, combining volume, margin and discount dependence.
    CASE
        WHEN r.units_sold = 0                                   THEN 'No Sales'
        WHEN r.revenue_rank <= 20 AND r.margin_pct >= 40        THEN 'Star'
        WHEN r.revenue_rank <= 20                               THEN 'Volume Driver'
        WHEN r.margin_pct >= 50 AND r.units_90d > 0             THEN 'Margin Gem'
        WHEN r.discount_rate_pct >= 15                          THEN 'Discount Dependent'
        WHEN r.units_90d = 0                                    THEN 'Dormant'
        ELSE 'Steady'
    END                                                                        AS performance_segment
FROM ranked r;
