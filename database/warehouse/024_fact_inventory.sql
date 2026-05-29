-- ===========================================================================
-- gold.fact_inventory - grain: ONE PRODUCT, ONE WEEKLY SNAPSHOT.
--
-- A periodic-snapshot fact (Kimball's second fact type). Balances are
-- semi-additive: they sum across products but NOT across dates, so every mart
-- that reports stock takes the latest snapshot rather than a SUM over time.
-- ===========================================================================

DROP TABLE IF EXISTS gold.fact_inventory;
CREATE TABLE gold.fact_inventory AS
SELECT
    i.inventory_id                                      AS inventory_key,
    d.date_key                                          AS snapshot_date_key,
    i.snapshot_date,
    COALESCE(p.product_key, -1)                         AS product_key,
    i.product_id,
    i.on_hand_units,
    i.reorder_point,
    i.units_sold,
    i.restock_units,
    ROUND(i.on_hand_units * COALESCE(p.unit_cost, 0), 2) AS on_hand_value_at_cost,
    ROUND(i.on_hand_units * COALESCE(p.unit_price, 0), 2) AS on_hand_value_at_retail,
    i.days_of_cover,
    i.is_stockout,
    i.is_below_reorder,
    i.is_excess_stock,
    -- Lost sales proxy: a stockout week is charged the product's own trailing
    -- average weekly sell-through. Approximate by design, and documented as
    -- such in docs/kpi-definitions.md.
    CASE WHEN i.is_stockout
         THEN ROUND(AVG(i.units_sold) OVER (PARTITION BY i.product_id)
                    * COALESCE(p.unit_price, 0), 2)
         ELSE 0 END                                     AS estimated_lost_revenue
FROM silver.inventory_snapshots i
JOIN gold.dim_date d ON d.date_value = i.snapshot_date
LEFT JOIN gold.dim_product p ON p.product_id = i.product_id;
