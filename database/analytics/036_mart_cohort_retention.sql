-- ===========================================================================
-- gold.mart_cohort_retention - monthly acquisition cohorts x months since.
--
-- Cohort = the calendar month of a customer's FIRST completed order (not their
-- signup month - a signup that never bought is not a retention story, it is an
-- activation story, and mixing the two is the most common way this chart lies).
--
-- Two measures per cell:
--   retained_customers / retention_pct  - do they come back
--   cohort_revenue     / cumulative_ltv - are they worth keeping
--
-- The table is dense only where a cohort could have been observed: a cohort
-- acquired last month has no month-6 cell, and we emit no row rather than a
-- misleading zero.
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_cohort_retention;
CREATE TABLE gold.mart_cohort_retention AS
WITH win AS (
    SELECT * FROM gold.analysis_window
),
first_order AS (
    SELECT
        o.customer_key,
        MIN(o.order_date) AS first_order_date,
        CAST(DATE_TRUNC('month', CAST(MIN(o.order_date) AS TIMESTAMP)) AS DATE) AS cohort_month
    FROM gold.fact_orders o
    WHERE o.is_revenue
    GROUP BY o.customer_key
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS cohort_customers
    FROM first_order
    GROUP BY cohort_month
),
activity AS (
    SELECT
        f.cohort_month,
        CAST(DATE_TRUNC('month', CAST(o.order_date AS TIMESTAMP)) AS DATE) AS activity_month,
        -- Whole months between acquisition and activity.
        CAST(
            (EXTRACT(YEAR FROM o.order_date) - EXTRACT(YEAR FROM f.cohort_month)) * 12
          + (EXTRACT(MONTH FROM o.order_date) - EXTRACT(MONTH FROM f.cohort_month))
        AS INTEGER)                                             AS months_since,
        o.customer_key,
        o.net_amount,
        o.gross_profit
    FROM gold.fact_orders o
    JOIN first_order f ON f.customer_key = o.customer_key
    WHERE o.is_revenue
),
cells AS (
    SELECT
        cohort_month,
        activity_month,
        months_since,
        COUNT(DISTINCT customer_key)                            AS retained_customers,
        COUNT(*)                                                AS orders,
        ROUND(SUM(net_amount), 2)                               AS cohort_revenue,
        ROUND(SUM(gross_profit), 2)                             AS cohort_profit
    FROM activity
    GROUP BY cohort_month, activity_month, months_since
)
SELECT
    c.cohort_month,
    c.activity_month,
    c.months_since,
    cs.cohort_customers,
    c.retained_customers,
    c.orders,
    c.cohort_revenue,
    c.cohort_profit,
    ROUND(CAST(c.retained_customers AS DOUBLE PRECISION) / cs.cohort_customers * 100, 2)
                                                                AS retention_pct,
    ROUND(c.cohort_revenue / cs.cohort_customers, 2)            AS revenue_per_cohort_customer,
    -- Cumulative LTV curve: what one acquired customer has returned by month N.
    ROUND(SUM(c.cohort_revenue) OVER (
            PARTITION BY c.cohort_month ORDER BY c.months_since
          ) / cs.cohort_customers, 2)                           AS cumulative_ltv,
    ROUND(SUM(c.cohort_profit) OVER (
            PARTITION BY c.cohort_month ORDER BY c.months_since
          ) / cs.cohort_customers, 2)                           AS cumulative_profit_per_customer
FROM cells c
JOIN cohort_size cs ON cs.cohort_month = c.cohort_month
ORDER BY c.cohort_month, c.months_since;

-- ---------------------------------------------------------------------------
-- gold.mart_retention_summary - the headline numbers pulled out of the grid.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.mart_retention_summary;
CREATE TABLE gold.mart_retention_summary AS
SELECT
    cohort_month,
    MAX(cohort_customers)                                       AS cohort_customers,
    MAX(retention_pct) FILTER (WHERE months_since = 1)          AS m1_retention_pct,
    MAX(retention_pct) FILTER (WHERE months_since = 3)          AS m3_retention_pct,
    MAX(retention_pct) FILTER (WHERE months_since = 6)          AS m6_retention_pct,
    MAX(retention_pct) FILTER (WHERE months_since = 12)         AS m12_retention_pct,
    MAX(cumulative_ltv) FILTER (WHERE months_since = 3)         AS ltv_m3,
    MAX(cumulative_ltv) FILTER (WHERE months_since = 6)         AS ltv_m6,
    MAX(cumulative_ltv) FILTER (WHERE months_since = 12)        AS ltv_m12,
    ROUND(SUM(cohort_revenue), 2)                               AS cohort_revenue_to_date,
    ROUND(SUM(cohort_revenue) / MAX(cohort_customers), 2)       AS ltv_to_date,
    MAX(months_since)                                           AS months_observed
FROM gold.mart_cohort_retention
GROUP BY cohort_month;

-- ---------------------------------------------------------------------------
-- gold.mart_churn_monthly - the flow view: who left, who came back.
--
-- A customer is "churned in month M" when they were active in the trailing
-- window before M and placed no order within CHURN_WINDOW_DAYS afterwards.
-- Expressed here as a month-over-month set difference, which is the version
-- an analyst can verify by hand.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.mart_churn_monthly;
CREATE TABLE gold.mart_churn_monthly AS
WITH monthly_active AS (
    SELECT DISTINCT
        CAST(DATE_TRUNC('month', CAST(order_date AS TIMESTAMP)) AS DATE) AS activity_month,
        customer_key
    FROM gold.fact_orders
    WHERE is_revenue
),
months AS (
    SELECT DISTINCT activity_month FROM monthly_active
),
seq AS (
    SELECT
        activity_month,
        LAG(activity_month) OVER (ORDER BY activity_month) AS prev_month
    FROM months
),
flows AS (
    SELECT
        s.activity_month,
        COUNT(DISTINCT cur.customer_key)                                        AS active_customers,
        COUNT(DISTINCT cur.customer_key) FILTER (WHERE prv.customer_key IS NULL) AS acquired_or_returned,
        (SELECT COUNT(DISTINCT p.customer_key)
         FROM monthly_active p
         WHERE p.activity_month = s.prev_month
           AND NOT EXISTS (SELECT 1 FROM monthly_active n
                           WHERE n.activity_month = s.activity_month
                             AND n.customer_key = p.customer_key))              AS churned_customers,
        (SELECT COUNT(DISTINCT p.customer_key)
         FROM monthly_active p
         WHERE p.activity_month = s.prev_month)                                 AS prev_active_customers
    FROM seq s
    JOIN monthly_active cur ON cur.activity_month = s.activity_month
    LEFT JOIN monthly_active prv
           ON prv.activity_month = s.prev_month AND prv.customer_key = cur.customer_key
    GROUP BY s.activity_month, s.prev_month
)
SELECT
    activity_month,
    active_customers,
    prev_active_customers,
    acquired_or_returned,
    churned_customers,
    active_customers - acquired_or_returned                                     AS retained_customers,
    CASE WHEN prev_active_customers > 0
         THEN ROUND(CAST(churned_customers AS DOUBLE PRECISION) / prev_active_customers * 100, 2)
         ELSE NULL END                                                          AS churn_rate_pct,
    CASE WHEN prev_active_customers > 0
         THEN ROUND(CAST(active_customers - acquired_or_returned AS DOUBLE PRECISION)
                    / prev_active_customers * 100, 2)
         ELSE NULL END                                                          AS retention_rate_pct
FROM flows
ORDER BY activity_month;
