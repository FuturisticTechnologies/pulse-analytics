-- ===========================================================================
-- gold.fact_payments - grain: ONE PAYMENT ATTEMPT.
--
-- Keeping every attempt (not just the successful one) is what lets operations
-- answer the questions that actually cost money: which issuer declines are
-- recoverable on retry, which methods fail most, and how much revenue is stuck
-- behind failures right now.
-- ===========================================================================

DROP TABLE IF EXISTS gold.fact_payments;
CREATE TABLE gold.fact_payments AS
SELECT
    p.payment_id                                        AS payment_key,
    p.order_id,
    d.date_key                                          AS payment_date_key,
    p.payment_date,
    p.payment_ts,
    COALESCE(pm.payment_method_key, -1)                 AS payment_method_key,
    p.payment_method,
    COALESCE(o.customer_key, -1)                        AS customer_key,
    COALESCE(o.region_key,   -1)                        AS region_key,
    COALESCE(o.store_key,    -1)                        AS store_key,
    p.amount,
    p.status                                            AS payment_status,
    p.failure_reason,
    p.failure_category,
    p.attempt_number,
    p.is_final_attempt,
    p.is_captured,
    p.is_failed,
    p.is_refunded,
    -- Seconds between the order being placed and this attempt: authorisation
    -- latency, which spikes when the payment gateway degrades.
    CAST(EXTRACT(EPOCH FROM (p.payment_ts - o.order_ts)) AS BIGINT) AS seconds_after_order
FROM silver.payments p
JOIN gold.dim_date d ON d.date_value = p.payment_date
LEFT JOIN gold.fact_orders o ON o.order_key = p.order_id
LEFT JOIN gold.dim_payment_method pm ON pm.payment_method = p.payment_method;
