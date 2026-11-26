-- ===========================================================================
-- gold.mart_order_exceptions - cancellations and returns by reason (PULA-105).
--
-- Two denominators, both kept and both named:
--   share_of_outcome_pct     = orders / outcome_orders
--       "of all returns, how many were for this reason" - what to fix first.
--   rate_of_orders_placed_pct = orders / orders_placed
--       "per 100 orders placed, how many came back for this reason" - the
--       number that moves when a fix works, and the one comparable over time.
--
-- Reasons are mapped to a label and a group here, once. A blank reason is
-- reported as 'Not recorded' and a code with no mapping as 'Unmapped' - both
-- stay visible on the page instead of quietly falling out of the totals.
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_order_exceptions;
CREATE TABLE gold.mart_order_exceptions AS
WITH reason_map AS (
    SELECT 'Cancelled' AS outcome, 'customer_request' AS reason_code,
           'Customer asked to cancel' AS reason_label, 'Customer' AS reason_group
    UNION ALL SELECT 'Cancelled', 'payment_failed',     'Payment failed',          'Payment'
    UNION ALL SELECT 'Cancelled', 'out_of_stock',       'Out of stock',            'Inventory'
    UNION ALL SELECT 'Cancelled', 'delivery_too_slow',  'Delivery too slow',       'Fulfilment'
    UNION ALL SELECT 'Cancelled', 'duplicate_order',    'Duplicate order',         'Customer'
    UNION ALL SELECT 'Cancelled', 'fraud_review',       'Failed fraud review',     'Payment'
    UNION ALL SELECT 'Returned',  'size_or_fit',        'Size or fit',             'Product'
    UNION ALL SELECT 'Returned',  'not_as_described',   'Not as described',        'Product'
    UNION ALL SELECT 'Returned',  'damaged_in_transit', 'Damaged in transit',      'Fulfilment'
    UNION ALL SELECT 'Returned',  'defective',          'Defective',               'Product'
    UNION ALL SELECT 'Returned',  'changed_mind',       'Changed mind',            'Customer'
    UNION ALL SELECT 'Returned',  'wrong_item_sent',    'Wrong item sent',         'Fulfilment'
    UNION ALL SELECT 'Returned',  'arrived_late',       'Arrived late',            'Fulfilment'
),
periods AS (
    SELECT 'Last 90 days' AS period, 1 AS period_order, w.trailing_90_start AS period_start
    FROM gold.analysis_window w
    UNION ALL
    SELECT 'All history', 2, w.first_date
    FROM gold.analysis_window w
),
placed AS (
    SELECT pr.period, COUNT(*) AS orders_placed
    FROM gold.fact_orders o
    JOIN periods pr ON o.order_date >= pr.period_start
    GROUP BY pr.period
),
exceptions AS (
    SELECT
        pr.period,
        pr.period_order,
        CASE WHEN o.is_cancelled THEN 'Cancelled' ELSE 'Returned' END  AS outcome,
        COALESCE(o.order_status_reason, 'not_recorded')                AS reason_code,
        o.total_amount
    FROM gold.fact_orders o
    JOIN periods pr ON o.order_date >= pr.period_start
    WHERE o.is_cancelled OR o.is_returned
),
counted AS (
    SELECT
        e.period,
        e.period_order,
        e.outcome,
        e.reason_code,
        COALESCE(m.reason_label,
                 CASE WHEN e.reason_code = 'not_recorded' THEN 'Not recorded'
                      ELSE e.reason_code END)                          AS reason_label,
        COALESCE(m.reason_group,
                 CASE WHEN e.reason_code = 'not_recorded' THEN 'Not recorded'
                      ELSE 'Unmapped' END)                             AS reason_group,
        CASE WHEN m.reason_code IS NOT NULL THEN TRUE ELSE FALSE END   AS is_mapped,
        COUNT(*)                                                       AS orders,
        ROUND(SUM(e.total_amount), 2)                                  AS order_value
    FROM exceptions e
    LEFT JOIN reason_map m ON m.outcome = e.outcome AND m.reason_code = e.reason_code
    GROUP BY e.period, e.period_order, e.outcome, e.reason_code,
             m.reason_label, m.reason_group, m.reason_code
)
SELECT
    c.period,
    c.period_order,
    c.outcome,
    c.reason_code,
    c.reason_label,
    c.reason_group,
    c.is_mapped,
    c.orders,
    c.order_value,
    SUM(c.orders) OVER (PARTITION BY c.period, c.outcome)              AS outcome_orders,
    p.orders_placed,
    ROUND(CAST(c.orders AS DOUBLE PRECISION)
          / NULLIF(SUM(c.orders) OVER (PARTITION BY c.period, c.outcome), 0) * 100, 2)
                                                                       AS share_of_outcome_pct,
    ROUND(CAST(c.orders AS DOUBLE PRECISION)
          / NULLIF(p.orders_placed, 0) * 100, 2)                       AS rate_of_orders_placed_pct
FROM counted c
JOIN placed p ON p.period = c.period;

-- ---------------------------------------------------------------------------
-- Monthly cancellation and return rates - is a fix working, or is a problem
-- growing. Rates are per order placed in the same month (a ratio of counts,
-- never an average of daily rates), so a busy month does not look like a
-- worse one.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.mart_order_exceptions_monthly;
CREATE TABLE gold.mart_order_exceptions_monthly AS
WITH monthly_placed AS (
    SELECT
        CAST(DATE_TRUNC('month', CAST(order_date AS TIMESTAMP)) AS DATE) AS month_start,
        COUNT(*)                                                       AS orders_placed,
        COUNT(*) FILTER (WHERE is_cancelled)                           AS orders_cancelled,
        COUNT(*) FILTER (WHERE is_returned)                            AS orders_returned
    FROM gold.fact_orders
    GROUP BY 1
)
SELECT
    month_start,
    orders_placed,
    orders_cancelled,
    orders_returned,
    ROUND(CAST(orders_cancelled AS DOUBLE PRECISION)
          / NULLIF(orders_placed, 0) * 100, 2)                         AS cancellation_rate_pct,
    ROUND(CAST(orders_returned AS DOUBLE PRECISION)
          / NULLIF(orders_placed, 0) * 100, 2)                         AS return_rate_pct
FROM monthly_placed;
