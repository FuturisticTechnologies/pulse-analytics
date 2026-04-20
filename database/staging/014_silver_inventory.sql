-- ===========================================================================
-- Silver: weekly inventory snapshots.
--
-- Adds the derived signals the operations dashboard runs on: cover in days,
-- below-reorder-point flag, and an excess-stock flag. Days-of-cover uses the
-- snapshot's own sell-through, so a product that sells nothing gets NULL
-- rather than a misleading "infinite cover".
-- ===========================================================================

DROP TABLE IF EXISTS silver.inventory_snapshots;
CREATE TABLE silver.inventory_snapshots AS
SELECT
    inventory_id,
    snapshot_date,
    CAST(DATE_TRUNC('month', CAST(snapshot_date AS TIMESTAMP)) AS DATE) AS snapshot_month,
    product_id,
    GREATEST(COALESCE(on_hand_units, 0), 0)     AS on_hand_units,
    GREATEST(COALESCE(reorder_point, 0), 0)     AS reorder_point,
    GREATEST(COALESCE(units_sold, 0), 0)        AS units_sold,
    GREATEST(COALESCE(restock_units, 0), 0)     AS restock_units,
    COALESCE(is_stockout, FALSE)                AS is_stockout,
    CASE
        WHEN COALESCE(units_sold, 0) > 0
        THEN ROUND(CAST(on_hand_units AS DOUBLE PRECISION) / (units_sold / 7.0), 1)
        ELSE NULL
    END                                         AS days_of_cover,
    CASE WHEN COALESCE(on_hand_units, 0) <= COALESCE(reorder_point, 0)
         THEN TRUE ELSE FALSE END               AS is_below_reorder,
    CASE WHEN COALESCE(units_sold, 0) > 0
              AND on_hand_units > units_sold * 8
         THEN TRUE ELSE FALSE END               AS is_excess_stock
FROM (
    SELECT b.*, ROW_NUMBER() OVER (PARTITION BY inventory_id ORDER BY _loaded_at DESC) AS _rn
    FROM bronze.inventory_snapshots b
    WHERE inventory_id IS NOT NULL AND product_id IS NOT NULL AND snapshot_date IS NOT NULL
) d
WHERE _rn = 1;
