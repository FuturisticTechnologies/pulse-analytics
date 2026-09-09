-- ===========================================================================
-- Silver: payments.
--
-- One order can have several attempts (a decline followed by a retry) plus a
-- later refund. `is_final_attempt` marks the attempt that decided the order's
-- fate, which is what the payment-success KPI must be measured on - counting
-- every raw row would make the failure rate look worse than it is.
-- ===========================================================================

DROP TABLE IF EXISTS silver.payments;
CREATE TABLE silver.payments AS
WITH deduped AS (
    SELECT b.*, ROW_NUMBER() OVER (PARTITION BY payment_id ORDER BY _loaded_at DESC) AS _rn
    FROM bronze.payments b
    WHERE payment_id IS NOT NULL AND order_id IS NOT NULL
), ranked AS (
    SELECT
        payment_id,
        order_id,
        TRIM(payment_method)                       AS payment_method,
        payment_ts,
        CAST(payment_ts AS DATE)                   AS payment_date,
        ROUND(COALESCE(amount, 0), 2)              AS amount,
        LOWER(TRIM(status))                        AS status,
        NULLIF(TRIM(COALESCE(failure_reason, '')), '') AS failure_reason,
        COALESCE(attempt_number, 1)                AS attempt_number,
        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY COALESCE(attempt_number, 1) DESC, payment_ts DESC
        )                                          AS _attempt_rank
    FROM deduped
    WHERE _rn = 1
)
SELECT
    payment_id,
    order_id,
    payment_method,
    payment_ts,
    payment_date,
    CAST(DATE_TRUNC('month', payment_ts) AS DATE)  AS payment_month,
    amount,
    status,
    failure_reason,
    attempt_number,
    CASE WHEN _attempt_rank = 1 THEN TRUE ELSE FALSE END AS is_final_attempt,
    CASE WHEN status = 'captured' THEN TRUE ELSE FALSE END AS is_captured,
    CASE WHEN status = 'failed'   THEN TRUE ELSE FALSE END AS is_failed,
    CASE WHEN status = 'refunded' THEN TRUE ELSE FALSE END AS is_refunded,
    CASE
        WHEN failure_reason IN ('insufficient_funds', 'card_expired', 'do_not_honor', 'invalid_cvc')
             THEN 'Issuer decline'
        WHEN failure_reason = 'network_timeout'  THEN 'Technical'
        WHEN failure_reason = 'fraud_suspected'  THEN 'Risk'
        ELSE NULL
    END                                            AS failure_category
FROM ranked;
