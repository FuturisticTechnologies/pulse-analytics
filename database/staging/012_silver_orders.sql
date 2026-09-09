-- ===========================================================================
-- Silver: orders and order lines.
--
-- Two real problems are fixed here:
--   1. the source replays a small number of orders verbatim -> de-duplicate
--      on order_id, keeping one row (they are identical, so ordering is only
--      for determinism);
--   2. some order lines carry a negative quantity from a returns-integration
--      bug -> take the absolute value and recompute the money columns from
--      first principles rather than trusting the pre-computed totals.
-- ===========================================================================

DROP TABLE IF EXISTS silver.order_items;
CREATE TABLE silver.order_items AS
SELECT
    order_item_id,
    order_id,
    product_id,
    ABS(quantity)                                       AS quantity,
    unit_price,
    unit_cost,
    COALESCE(discount_amount, 0)                        AS discount_amount,
    ROUND(ABS(quantity) * unit_price, 2)                AS gross_amount,
    ROUND(ABS(quantity) * unit_price - COALESCE(discount_amount, 0), 2) AS line_amount,
    ROUND(ABS(quantity) * unit_cost, 2)                 AS line_cost,
    ROUND(ABS(quantity) * unit_price - COALESCE(discount_amount, 0)
          - ABS(quantity) * unit_cost, 2)               AS line_profit,
    CASE WHEN quantity < 0 THEN TRUE ELSE FALSE END     AS was_negative_quantity
FROM (
    SELECT b.*, ROW_NUMBER() OVER (PARTITION BY order_item_id ORDER BY _loaded_at DESC) AS _rn
    FROM bronze.order_items b
    WHERE order_item_id IS NOT NULL
      AND order_id      IS NOT NULL
      AND product_id    IS NOT NULL
      AND quantity      IS NOT NULL
      AND quantity     <> 0
) d
WHERE _rn = 1;

DROP TABLE IF EXISTS silver.orders;
CREATE TABLE silver.orders AS
WITH deduped AS (
    SELECT b.*, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY _loaded_at DESC, order_ts DESC) AS _rn
    FROM bronze.orders b
    WHERE order_id IS NOT NULL
      AND customer_id IS NOT NULL
      AND order_ts IS NOT NULL
), line_totals AS (
    SELECT
        order_id,
        SUM(quantity)     AS items_units,
        COUNT(*)          AS items_lines,
        SUM(gross_amount) AS items_gross,
        SUM(discount_amount) AS items_discount,
        SUM(line_amount)  AS items_net,
        SUM(line_cost)    AS items_cost
    FROM silver.order_items
    GROUP BY order_id
)
SELECT
    d.order_id,
    d.customer_id,
    d.store_id,
    d.order_ts,
    CAST(d.order_ts AS DATE)                                     AS order_date,
    CAST(DATE_TRUNC('month', d.order_ts) AS DATE)                AS order_month,
    CAST(DATE_TRUNC('week',  d.order_ts) AS DATE)                AS order_week,
    CAST(EXTRACT(HOUR FROM d.order_ts) AS INTEGER)               AS order_hour,
    TRIM(d.channel)                                              AS channel,
    LOWER(TRIM(d.status))                                        AS status,
    COALESCE(NULLIF(TRIM(d.currency), ''), 'USD')                AS currency,
    CAST(d.campaign_id AS INTEGER)                               AS campaign_id,
    COALESCE(lt.items_lines, 0)                                  AS line_count,
    COALESCE(lt.items_units, 0)                                  AS item_count,
    ROUND(COALESCE(lt.items_gross, 0), 2)                        AS gross_amount,
    ROUND(COALESCE(lt.items_discount, 0), 2)                     AS discount_amount,
    ROUND(COALESCE(d.shipping_amount, 0), 2)                     AS shipping_amount,
    ROUND(COALESCE(d.tax_amount, 0), 2)                          AS tax_amount,
    ROUND(COALESCE(lt.items_net, 0), 2)                          AS net_amount,
    ROUND(COALESCE(lt.items_net, 0) + COALESCE(d.shipping_amount, 0)
          + COALESCE(d.tax_amount, 0), 2)                        AS total_amount,
    ROUND(COALESCE(lt.items_cost, 0), 2)                         AS cost_amount,
    ROUND(COALESCE(lt.items_net, 0) - COALESCE(lt.items_cost, 0), 2) AS gross_profit,
    -- Revenue recognition: only completed orders count towards revenue KPIs.
    CASE WHEN LOWER(TRIM(d.status)) = 'completed' THEN TRUE ELSE FALSE END AS is_revenue,
    CASE WHEN LOWER(TRIM(d.status)) = 'returned'  THEN TRUE ELSE FALSE END AS is_returned,
    CASE WHEN LOWER(TRIM(d.status)) = 'cancelled' THEN TRUE ELSE FALSE END AS is_cancelled,
    CASE WHEN d.campaign_id IS NOT NULL THEN TRUE ELSE FALSE END           AS is_campaign_attributed
FROM deduped d
LEFT JOIN line_totals lt ON lt.order_id = d.order_id
WHERE d._rn = 1;
