-- ===========================================================================
-- gold.fact_customer_events - grain: ONE CLICKSTREAM EVENT.
--
-- Behavioural facts sit in the same star as the transactional ones so a single
-- query can ask "of the customers who viewed this product, what fraction
-- bought it" without leaving the warehouse.
-- ===========================================================================

DROP TABLE IF EXISTS gold.fact_customer_events;
CREATE TABLE gold.fact_customer_events AS
SELECT
    e.event_id                                          AS event_key,
    d.date_key                                          AS event_date_key,
    e.event_date,
    e.event_ts,
    e.event_hour,
    COALESCE(c.customer_key, -1)                        AS customer_key,
    COALESCE(p.product_key,  -1)                        AS product_key,
    e.event_type,
    e.funnel_step,
    e.session_id,
    e.device,
    e.device_class,
    e.duration_seconds,
    e.is_orphan_customer,
    CASE WHEN e.event_type = 'purchase'       THEN TRUE ELSE FALSE END AS is_conversion,
    CASE WHEN e.event_type = 'support_ticket' THEN TRUE ELSE FALSE END AS is_support_contact
FROM silver.customer_events e
JOIN gold.dim_date d ON d.date_value = e.event_date
LEFT JOIN gold.dim_customer c ON c.customer_id = e.customer_id
LEFT JOIN gold.dim_product  p ON p.product_id  = e.product_id;
