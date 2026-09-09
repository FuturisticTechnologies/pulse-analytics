-- ===========================================================================
-- gold.mart_conversion_funnel - session-level behavioural funnel.
--
-- Counted on SESSIONS, not events: a customer who views ten products in one
-- visit is one session that reached the product-view step, not ten. Steps are
-- "reached at least this stage", so the funnel is monotonically decreasing by
-- construction and cannot produce the impossible >100% step conversion that
-- event-counted funnels routinely show.
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_conversion_funnel;
CREATE TABLE gold.mart_conversion_funnel AS
WITH session_reach AS (
    SELECT
        session_id,
        MIN(event_date)                                         AS session_date,
        MAX(device_class)                                       AS device_class,
        MAX(funnel_step)                                        AS deepest_step
    FROM gold.fact_customer_events
    WHERE funnel_step > 0
    GROUP BY session_id
),
steps AS (
    SELECT 1 AS step_number, 'App / site open' AS step_name UNION ALL
    SELECT 2, 'Browsed a page'                 UNION ALL
    SELECT 3, 'Searched'                       UNION ALL
    SELECT 4, 'Viewed a product'               UNION ALL
    SELECT 5, 'Added to cart'                  UNION ALL
    SELECT 6, 'Started checkout'               UNION ALL
    SELECT 7, 'Purchased'
),
counted AS (
    SELECT
        s.step_number,
        s.step_name,
        COUNT(sr.session_id)                                    AS sessions
    FROM steps s
    LEFT JOIN session_reach sr ON sr.deepest_step >= s.step_number
    GROUP BY s.step_number, s.step_name
)
SELECT
    step_number,
    step_name,
    sessions,
    MAX(sessions) OVER ()                                       AS top_of_funnel,
    ROUND(CAST(sessions AS DOUBLE PRECISION)
          / NULLIF(MAX(sessions) OVER (), 0) * 100, 2)          AS pct_of_top,
    LAG(sessions) OVER (ORDER BY step_number)                   AS prev_step_sessions,
    ROUND(CAST(sessions AS DOUBLE PRECISION)
          / NULLIF(LAG(sessions) OVER (ORDER BY step_number), 0) * 100, 2) AS step_conversion_pct,
    COALESCE(LAG(sessions) OVER (ORDER BY step_number), sessions) - sessions AS dropped_sessions
FROM counted
ORDER BY step_number;

-- ---------------------------------------------------------------------------
-- Same funnel split by device class - where the mobile experience leaks.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.mart_funnel_by_device;
CREATE TABLE gold.mart_funnel_by_device AS
WITH session_reach AS (
    SELECT
        session_id,
        MAX(device_class)   AS device_class,
        MAX(funnel_step)    AS deepest_step
    FROM gold.fact_customer_events
    WHERE funnel_step > 0
    GROUP BY session_id
)
SELECT
    device_class,
    COUNT(*)                                                        AS sessions,
    COUNT(*) FILTER (WHERE deepest_step >= 4)                       AS reached_product_view,
    COUNT(*) FILTER (WHERE deepest_step >= 5)                       AS reached_add_to_cart,
    COUNT(*) FILTER (WHERE deepest_step >= 6)                       AS reached_checkout,
    COUNT(*) FILTER (WHERE deepest_step >= 7)                       AS reached_purchase,
    ROUND(CAST(COUNT(*) FILTER (WHERE deepest_step >= 7) AS DOUBLE PRECISION)
          / NULLIF(COUNT(*), 0) * 100, 2)                           AS conversion_rate_pct,
    ROUND(CAST(COUNT(*) FILTER (WHERE deepest_step >= 7) AS DOUBLE PRECISION)
          / NULLIF(COUNT(*) FILTER (WHERE deepest_step >= 5), 0) * 100, 2) AS cart_completion_pct,
    ROUND(100 - CAST(COUNT(*) FILTER (WHERE deepest_step >= 7) AS DOUBLE PRECISION)
          / NULLIF(COUNT(*) FILTER (WHERE deepest_step >= 5), 0) * 100, 2) AS cart_abandonment_pct
FROM session_reach
GROUP BY device_class;

-- ===========================================================================
-- gold.mart_payment_health - payment reliability, the operations view.
--
-- Measured on FINAL attempts for the order-level success rate and on ALL
-- attempts for the gateway-level failure rate. Both numbers are legitimate and
-- they answer different questions, so both are exposed with explicit names
-- rather than one ambiguous "success rate".
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_payment_health;
CREATE TABLE gold.mart_payment_health AS
SELECT
    p.payment_date,
    p.payment_method,
    pm.method_family,
    COUNT(*)                                                        AS attempts,
    COUNT(*) FILTER (WHERE p.is_captured)                           AS captured,
    COUNT(*) FILTER (WHERE p.is_failed)                             AS failed,
    COUNT(*) FILTER (WHERE p.is_refunded)                           AS refunded,
    COUNT(DISTINCT p.order_id)                                      AS orders,
    COUNT(DISTINCT p.order_id) FILTER (WHERE p.is_final_attempt AND p.is_captured)
                                                                    AS orders_paid,
    ROUND(SUM(p.amount) FILTER (WHERE p.is_captured), 2)            AS captured_amount,
    ROUND(SUM(p.amount) FILTER (WHERE p.is_failed), 2)              AS failed_amount,
    ROUND(SUM(p.amount) FILTER (WHERE p.is_refunded), 2)            AS refunded_amount,
    ROUND(CAST(COUNT(*) FILTER (WHERE p.is_failed) AS DOUBLE PRECISION)
          / NULLIF(COUNT(*), 0) * 100, 2)                           AS attempt_failure_rate_pct,
    ROUND(CAST(COUNT(DISTINCT p.order_id) FILTER (WHERE p.is_final_attempt AND p.is_captured)
               AS DOUBLE PRECISION)
          / NULLIF(COUNT(DISTINCT p.order_id), 0) * 100, 2)         AS order_success_rate_pct,
    ROUND(AVG(CAST(p.seconds_after_order AS DOUBLE PRECISION)), 1)  AS avg_auth_latency_sec,
    ROUND(AVG(CAST(p.attempt_number AS DOUBLE PRECISION)), 2)       AS avg_attempts_per_payment
FROM gold.fact_payments p
LEFT JOIN gold.dim_payment_method pm ON pm.payment_method_key = p.payment_method_key
GROUP BY p.payment_date, p.payment_method, pm.method_family;

-- ---------------------------------------------------------------------------
-- Why payments fail - ranked, with the recoverable ones called out.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.mart_payment_failures;
CREATE TABLE gold.mart_payment_failures AS
WITH flagged AS (
    -- Recovered = a later attempt on the same order was captured. Flag it per
    -- attempt first; aggregating a correlated lookup would be both wrong and
    -- unportable.
    SELECT
        f.failure_reason,
        f.failure_category,
        f.payment_method,
        f.amount,
        CASE WHEN EXISTS (
            SELECT 1 FROM gold.fact_payments r
            WHERE r.order_id = f.order_id
              AND r.is_captured
              AND r.attempt_number > f.attempt_number
        ) THEN 1 ELSE 0 END                                         AS was_recovered
    FROM gold.fact_payments f
    WHERE f.is_failed AND f.failure_reason IS NOT NULL
),
failures AS (
    SELECT
        failure_reason,
        failure_category,
        payment_method,
        COUNT(*)                                                    AS failures,
        ROUND(SUM(amount), 2)                                       AS amount_at_risk,
        SUM(was_recovered)                                          AS recovered
    FROM flagged
    GROUP BY failure_reason, failure_category, payment_method
)
SELECT
    failure_reason,
    failure_category,
    payment_method,
    failures,
    recovered,
    failures - recovered                                            AS lost,
    amount_at_risk,
    ROUND(CAST(recovered AS DOUBLE PRECISION) / NULLIF(failures, 0) * 100, 2) AS recovery_rate_pct,
    ROUND(CAST(failures AS DOUBLE PRECISION)
          / NULLIF(SUM(failures) OVER (), 0) * 100, 2)              AS share_of_failures_pct,
    CAST(RANK() OVER (ORDER BY failures DESC) AS INTEGER)           AS failure_rank
FROM failures;
