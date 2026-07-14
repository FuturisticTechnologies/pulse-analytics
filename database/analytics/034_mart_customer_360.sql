-- ===========================================================================
-- gold.mart_customer_360 - one row per customer, everything we know.
--
-- This is the table the customer dashboard, the CRM export and the churn model
-- all read. It deliberately mixes three kinds of column:
--   * descriptive  (who they are)        - from the dimension,
--   * behavioural  (what they have done) - aggregated from the facts,
--   * derived      (what we think)       - tenure, status, predicted value.
--
-- Recency is measured against gold.analysis_window.as_of_date, never the wall
-- clock, so the segmentation is reproducible.
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_customer_360;
CREATE TABLE gold.mart_customer_360 AS
WITH win AS (
    SELECT * FROM gold.analysis_window
),
order_stats AS (
    SELECT
        o.customer_key,
        COUNT(*)                                            AS orders,
        MIN(o.order_date)                                   AS first_order_date,
        MAX(o.order_date)                                   AS last_order_date,
        ROUND(SUM(o.net_amount), 2)                         AS lifetime_revenue,
        ROUND(SUM(o.gross_profit), 2)                       AS lifetime_profit,
        ROUND(SUM(o.discount_amount), 2)                    AS lifetime_discounts,
        SUM(o.item_count)                                   AS lifetime_units,
        ROUND(AVG(o.net_amount), 2)                         AS avg_order_value,
        ROUND(MAX(o.net_amount), 2)                         AS max_order_value,
        ROUND(AVG(o.days_since_prev_order), 1)              AS avg_days_between_orders
    FROM gold.fact_orders o
    WHERE o.is_revenue
    GROUP BY o.customer_key
),
recent_stats AS (
    SELECT
        o.customer_key,
        COUNT(*)                                            AS orders_90d,
        ROUND(SUM(o.net_amount), 2)                         AS revenue_90d
    FROM gold.fact_orders o
    CROSS JOIN win w
    WHERE o.is_revenue AND o.order_date >= w.trailing_90_start
    GROUP BY o.customer_key
),
prior_stats AS (
    SELECT
        o.customer_key,
        ROUND(SUM(o.net_amount), 2)                         AS revenue_prev_90d
    FROM gold.fact_orders o
    CROSS JOIN win w
    WHERE o.is_revenue
      AND o.order_date >= w.trailing_90_start - 90
      AND o.order_date <  w.trailing_90_start
    GROUP BY o.customer_key
),
return_stats AS (
    SELECT
        o.customer_key,
        COUNT(*) FILTER (WHERE o.is_returned)               AS orders_returned,
        COUNT(*) FILTER (WHERE o.is_cancelled)              AS orders_cancelled
    FROM gold.fact_orders o
    GROUP BY o.customer_key
),
-- Favourite category = the one the customer has spent most on. ROW_NUMBER
-- rather than MODE() because the tie-break must be deterministic.
favourite_category AS (
    SELECT customer_key, category AS favourite_category, category_revenue
    FROM (
        SELECT
            s.customer_key,
            p.category,
            ROUND(SUM(s.net_amount), 2) AS category_revenue,
            ROW_NUMBER() OVER (PARTITION BY s.customer_key
                               ORDER BY SUM(s.net_amount) DESC, p.category) AS rn
        FROM gold.fact_sales s
        JOIN gold.dim_product p ON p.product_key = s.product_key
        WHERE s.is_revenue
        GROUP BY s.customer_key, p.category
    ) t
    WHERE rn = 1
),
favourite_channel AS (
    SELECT customer_key, order_channel AS favourite_channel
    FROM (
        SELECT
            o.customer_key,
            o.order_channel,
            ROW_NUMBER() OVER (PARTITION BY o.customer_key
                               ORDER BY COUNT(*) DESC, o.order_channel) AS rn
        FROM gold.fact_orders o
        WHERE o.is_revenue
        GROUP BY o.customer_key, o.order_channel
    ) t
    WHERE rn = 1
),
engagement AS (
    SELECT
        e.customer_key,
        COUNT(*)                                            AS events_total,
        COUNT(DISTINCT e.session_id)                        AS sessions,
        COUNT(*) FILTER (WHERE e.is_support_contact)        AS support_contacts,
        MAX(e.event_date)                                   AS last_seen_date
    FROM gold.fact_customer_events e
    WHERE e.customer_key <> -1
    GROUP BY e.customer_key
)
SELECT
    c.customer_key,
    c.customer_id,
    c.full_name,
    c.email,
    c.city,
    c.region_key,
    c.acquisition_channel,
    c.age_band,
    c.gender,
    c.loyalty_tier,
    c.marketing_opt_in,
    c.signup_date,
    c.signup_month,
    CAST(w.as_of_date - c.signup_date AS INTEGER)                     AS tenure_days,
    COALESCE(os.orders, 0)                                            AS orders,
    COALESCE(os.lifetime_revenue, 0)                                  AS lifetime_revenue,
    COALESCE(os.lifetime_profit, 0)                                   AS lifetime_profit,
    COALESCE(os.lifetime_discounts, 0)                                AS lifetime_discounts,
    COALESCE(os.lifetime_units, 0)                                    AS lifetime_units,
    COALESCE(os.avg_order_value, 0)                                   AS avg_order_value,
    COALESCE(os.max_order_value, 0)                                   AS max_order_value,
    os.avg_days_between_orders,
    os.first_order_date,
    os.last_order_date,
    CASE WHEN os.last_order_date IS NULL THEN NULL
         ELSE CAST(w.as_of_date - os.last_order_date AS INTEGER) END  AS recency_days,
    COALESCE(rs.orders_90d, 0)                                        AS orders_90d,
    COALESCE(rs.revenue_90d, 0)                                       AS revenue_90d,
    COALESCE(ps.revenue_prev_90d, 0)                                  AS revenue_prev_90d,
    COALESCE(ret.orders_returned, 0)                                  AS orders_returned,
    COALESCE(ret.orders_cancelled, 0)                                 AS orders_cancelled,
    fc.favourite_category,
    fch.favourite_channel,
    COALESCE(en.events_total, 0)                                      AS events_total,
    COALESCE(en.sessions, 0)                                          AS sessions,
    COALESCE(en.support_contacts, 0)                                  AS support_contacts,
    en.last_seen_date,
    -- Lifecycle status. 'New' wins over 'Active' so acquisition cohorts are not
    -- double-counted in the retention view.
    CASE
        WHEN os.orders IS NULL                                              THEN 'Prospect'
        WHEN os.orders = 1 AND (w.as_of_date - os.last_order_date) <= 90     THEN 'New'
        WHEN (w.as_of_date - os.last_order_date) <= 90                       THEN 'Active'
        WHEN (w.as_of_date - os.last_order_date) <= 180                      THEN 'At Risk'
        WHEN (w.as_of_date - os.last_order_date) <= 365                      THEN 'Lapsed'
        ELSE 'Churned'
    END                                                               AS lifecycle_status,
    CASE WHEN os.orders IS NOT NULL AND (w.as_of_date - os.last_order_date) > 90
         THEN TRUE ELSE FALSE END                                     AS is_churned,
    CASE WHEN COALESCE(os.orders, 0) > 1 THEN TRUE ELSE FALSE END     AS is_repeat_buyer,
    -- Simple, explainable value projection: observed monthly spend rate held
    -- flat over the next 12 months. Deliberately not a black box - the
    -- Python model in analytics/customer/clv.py is the sophisticated version.
    CASE
        WHEN os.orders IS NULL OR (w.as_of_date - c.signup_date) < 30 THEN 0
        ELSE ROUND(os.lifetime_revenue
                   / (CAST(w.as_of_date - c.signup_date AS DOUBLE PRECISION) / 30.0)
                   * 12, 2)
    END                                                               AS projected_annual_value
FROM gold.dim_customer c
CROSS JOIN win w
LEFT JOIN order_stats       os  ON os.customer_key  = c.customer_key
LEFT JOIN recent_stats      rs  ON rs.customer_key  = c.customer_key
LEFT JOIN prior_stats       ps  ON ps.customer_key  = c.customer_key
LEFT JOIN return_stats      ret ON ret.customer_key = c.customer_key
LEFT JOIN favourite_category fc ON fc.customer_key  = c.customer_key
LEFT JOIN favourite_channel fch ON fch.customer_key = c.customer_key
LEFT JOIN engagement        en  ON en.customer_key  = c.customer_key
WHERE c.customer_key <> -1;
