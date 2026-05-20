-- ===========================================================================
-- gold.fact_sales - grain: ONE ORDER LINE.
--
-- This is the platform's atomic fact. Everything else (daily revenue, product
-- performance, basket analysis, margin) is an aggregate of this table, which
-- is why no mart is allowed to define revenue differently from `net_amount`
-- here. Cancelled and returned orders are kept, flagged, and excluded from
-- revenue by the `is_revenue` flag rather than by being deleted - operations
-- needs to see cancellations.
-- ===========================================================================

DROP TABLE IF EXISTS gold.fact_sales;
CREATE TABLE gold.fact_sales AS
SELECT
    oi.order_item_id                                    AS sales_key,
    o.order_id,
    d.date_key                                          AS order_date_key,
    o.order_date,
    o.order_ts,
    COALESCE(c.customer_key, -1)                        AS customer_key,
    COALESCE(p.product_key,  -1)                        AS product_key,
    COALESCE(s.store_key,    -1)                        AS store_key,
    COALESCE(s.region_key,   -1)                        AS region_key,
    COALESCE(cp.campaign_key, -1)                       AS campaign_key,
    o.channel                                           AS order_channel,   -- degenerate dim
    o.status                                            AS order_status,    -- degenerate dim
    oi.quantity,
    oi.unit_price,
    oi.unit_cost,
    oi.gross_amount,
    oi.discount_amount,
    oi.line_amount                                      AS net_amount,
    oi.line_cost                                        AS cost_amount,
    oi.line_profit                                      AS gross_profit,
    CASE WHEN oi.line_amount > 0
         THEN ROUND(oi.line_profit / oi.line_amount * 100, 2)
         ELSE 0 END                                     AS margin_pct,
    o.is_revenue,
    o.is_returned,
    o.is_cancelled,
    o.is_campaign_attributed
FROM silver.order_items oi
JOIN silver.orders    o  ON o.order_id      = oi.order_id
JOIN gold.dim_date    d  ON d.date_value    = o.order_date
LEFT JOIN gold.dim_customer c ON c.customer_id = o.customer_id
LEFT JOIN gold.dim_product  p ON p.product_id  = oi.product_id
LEFT JOIN gold.dim_store    s ON s.store_id    = o.store_id
LEFT JOIN gold.dim_campaign cp ON cp.campaign_id = o.campaign_id;

-- ---------------------------------------------------------------------------
-- gold.fact_orders - grain: ONE ORDER HEADER.
--
-- Order-level measures (AOV, basket size, shipping, tax) must not be summed
-- from the line fact or they double-count. A separate header fact is the
-- standard Kimball answer and keeps both grains honest.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.fact_orders;
CREATE TABLE gold.fact_orders AS
SELECT
    o.order_id                                          AS order_key,
    d.date_key                                          AS order_date_key,
    o.order_date,
    o.order_ts,
    o.order_hour,
    COALESCE(c.customer_key, -1)                        AS customer_key,
    COALESCE(s.store_key,    -1)                        AS store_key,
    COALESCE(s.region_key,   -1)                        AS region_key,
    COALESCE(cp.campaign_key, -1)                       AS campaign_key,
    o.channel                                           AS order_channel,
    o.status                                            AS order_status,
    o.currency,
    o.line_count,
    o.item_count,
    o.gross_amount,
    o.discount_amount,
    o.shipping_amount,
    o.tax_amount,
    o.net_amount,
    o.total_amount,
    o.cost_amount,
    o.gross_profit,
    o.is_revenue,
    o.is_returned,
    o.is_cancelled,
    o.is_campaign_attributed,
    -- Sequence of this order in the customer's lifetime: 1 = acquisition.
    CAST(ROW_NUMBER() OVER (PARTITION BY o.customer_id ORDER BY o.order_ts) AS INTEGER)
                                                        AS customer_order_seq,
    CASE WHEN ROW_NUMBER() OVER (PARTITION BY o.customer_id ORDER BY o.order_ts) = 1
         THEN TRUE ELSE FALSE END                       AS is_first_order,
    -- Days since that customer's previous order - the input to repeat-rate and
    -- purchase-cadence analysis.
    CAST(o.order_date - LAG(o.order_date) OVER (PARTITION BY o.customer_id ORDER BY o.order_ts)
         AS INTEGER)                                    AS days_since_prev_order
FROM silver.orders o
JOIN gold.dim_date d ON d.date_value = o.order_date
LEFT JOIN gold.dim_customer c  ON c.customer_id = o.customer_id
LEFT JOIN gold.dim_store    s  ON s.store_id    = o.store_id
LEFT JOIN gold.dim_campaign cp ON cp.campaign_id = o.campaign_id;
