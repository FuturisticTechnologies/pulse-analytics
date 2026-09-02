-- ===========================================================================
-- gold.mart_inventory_health - current stock position, one row per product.
--
-- Reads only the LATEST snapshot per product. Inventory balances are
-- semi-additive: summing on_hand_units across weeks would report stock the
-- business never had. That is the single most common inventory-reporting bug,
-- so it is prevented structurally here rather than by convention.
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_inventory_health;
CREATE TABLE gold.mart_inventory_health AS
WITH latest AS (
    SELECT product_key, MAX(snapshot_date) AS snapshot_date
    FROM gold.fact_inventory
    GROUP BY product_key
),
current_stock AS (
    SELECT f.*
    FROM gold.fact_inventory f
    JOIN latest l ON l.product_key = f.product_key AND l.snapshot_date = f.snapshot_date
),
history AS (
    SELECT
        product_key,
        COUNT(*)                                                AS snapshots,
        SUM(CASE WHEN is_stockout THEN 1 ELSE 0 END)            AS stockout_weeks,
        ROUND(AVG(CAST(on_hand_units AS DOUBLE PRECISION)), 1)  AS avg_on_hand,
        ROUND(AVG(CAST(units_sold AS DOUBLE PRECISION)), 1)     AS avg_weekly_sales,
        SUM(units_sold)                                         AS units_sold_total,
        ROUND(SUM(estimated_lost_revenue), 2)                   AS estimated_lost_revenue
    FROM gold.fact_inventory
    GROUP BY product_key
)
SELECT
    p.product_key,
    p.product_id,
    p.sku,
    p.product_name,
    p.category,
    p.subcategory,
    p.brand,
    p.unit_price,
    p.unit_cost,
    cs.snapshot_date                                            AS as_of_date,
    cs.on_hand_units,
    cs.reorder_point,
    cs.units_sold                                               AS units_sold_last_week,
    cs.on_hand_value_at_cost,
    cs.on_hand_value_at_retail,
    cs.days_of_cover,
    cs.is_stockout,
    cs.is_below_reorder,
    cs.is_excess_stock,
    h.snapshots                                                 AS weeks_tracked,
    h.stockout_weeks,
    ROUND(CAST(h.stockout_weeks AS DOUBLE PRECISION)
          / NULLIF(h.snapshots, 0) * 100, 2)                    AS stockout_rate_pct,
    h.avg_on_hand,
    h.avg_weekly_sales,
    h.units_sold_total,
    h.estimated_lost_revenue,
    -- Inventory turns: annualised sell-through against average holding.
    CASE WHEN h.avg_on_hand > 0
         THEN ROUND(h.avg_weekly_sales * 52.0 / h.avg_on_hand, 2)
         ELSE NULL END                                          AS inventory_turns,
    -- The action list operations works from, in priority order.
    CASE
        WHEN cs.is_stockout                                     THEN 'Stockout - expedite'
        WHEN cs.is_below_reorder                                THEN 'Reorder now'
        WHEN cs.days_of_cover IS NOT NULL AND cs.days_of_cover < 14 THEN 'Low cover'
        WHEN cs.is_excess_stock                                 THEN 'Overstocked - markdown'
        WHEN h.avg_weekly_sales = 0                             THEN 'Dead stock'
        ELSE 'Healthy'
    END                                                         AS stock_status,
    CASE
        WHEN cs.is_stockout                                     THEN 1
        WHEN cs.is_below_reorder                                THEN 2
        WHEN cs.days_of_cover IS NOT NULL AND cs.days_of_cover < 14 THEN 3
        WHEN cs.is_excess_stock                                 THEN 4
        ELSE 5
    END                                                         AS action_priority
FROM gold.dim_product p
JOIN current_stock cs ON cs.product_key = p.product_key
LEFT JOIN history  h  ON h.product_key  = p.product_key
WHERE p.product_key <> -1;

-- ---------------------------------------------------------------------------
-- gold.mart_inventory_weekly - the trend line behind the current position.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.mart_inventory_weekly;
CREATE TABLE gold.mart_inventory_weekly AS
SELECT
    f.snapshot_date,
    p.category,
    COUNT(DISTINCT f.product_key)                               AS products,
    SUM(f.on_hand_units)                                        AS on_hand_units,
    ROUND(SUM(f.on_hand_value_at_cost), 2)                      AS stock_value_at_cost,
    ROUND(SUM(f.on_hand_value_at_retail), 2)                    AS stock_value_at_retail,
    SUM(f.units_sold)                                           AS units_sold,
    SUM(f.restock_units)                                        AS restock_units,
    SUM(CASE WHEN f.is_stockout THEN 1 ELSE 0 END)              AS stockout_products,
    ROUND(CAST(SUM(CASE WHEN f.is_stockout THEN 1 ELSE 0 END) AS DOUBLE PRECISION)
          / NULLIF(COUNT(DISTINCT f.product_key), 0) * 100, 2)  AS stockout_rate_pct,
    SUM(CASE WHEN f.is_below_reorder THEN 1 ELSE 0 END)         AS below_reorder_products,
    ROUND(SUM(f.estimated_lost_revenue), 2)                     AS estimated_lost_revenue
FROM gold.fact_inventory f
JOIN gold.dim_product p ON p.product_key = f.product_key
WHERE p.product_key <> -1
GROUP BY f.snapshot_date, p.category;
