-- ===========================================================================
-- gold.mart_campaign_performance - one row per campaign.
--
-- Attribution model: LAST-TOUCH, campaign-window. An order is credited to a
-- campaign when the source system stamped that campaign on it. This is the
-- honest limit of the available data and it is stated on the dashboard, because
-- an unlabelled ROAS number is worse than no ROAS number.
--
-- Incrementality is approximated by comparing revenue during the campaign
-- window against the same channel's baseline in the 28 days before it - a
-- crude proxy, flagged as such, but far more useful than raw attributed
-- revenue when comparing an always-on channel with a burst campaign.
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_campaign_performance;
CREATE TABLE gold.mart_campaign_performance AS
WITH attributed AS (
    SELECT
        o.campaign_key,
        COUNT(*)                                                AS attributed_orders,
        COUNT(DISTINCT o.customer_key)                          AS attributed_customers,
        COUNT(*) FILTER (WHERE o.is_first_order)                AS attributed_new_customers,
        ROUND(SUM(o.net_amount), 2)                             AS attributed_revenue,
        ROUND(SUM(o.gross_profit), 2)                           AS attributed_profit,
        ROUND(AVG(o.net_amount), 2)                             AS attributed_aov
    FROM gold.fact_orders o
    WHERE o.is_revenue AND o.campaign_key <> -1
    GROUP BY o.campaign_key
),
baseline AS (
    -- Average daily revenue in the 28 days immediately before the campaign,
    -- across all orders. The counterfactual "what would have happened anyway".
    SELECT
        c.campaign_key,
        ROUND(COALESCE(SUM(d.revenue), 0) / 28.0, 2)            AS baseline_daily_revenue
    FROM gold.dim_campaign c
    LEFT JOIN gold.mart_sales_daily d
           ON d.order_date >= c.start_date - 28
          AND d.order_date <  c.start_date
    WHERE c.campaign_key <> -1
    GROUP BY c.campaign_key
),
during AS (
    SELECT
        c.campaign_key,
        ROUND(COALESCE(SUM(d.revenue), 0), 2)                   AS window_total_revenue,
        COUNT(d.order_date)                                     AS window_days
    FROM gold.dim_campaign c
    LEFT JOIN gold.mart_sales_daily d
           ON d.order_date >= c.start_date AND d.order_date <= c.end_date
    WHERE c.campaign_key <> -1
    GROUP BY c.campaign_key
)
SELECT
    c.campaign_key,
    c.campaign_id,
    c.campaign_name,
    c.channel,
    c.objective,
    c.target_segment,
    c.start_date,
    c.end_date,
    c.duration_days,
    c.budget,
    c.spend,
    c.impressions,
    c.clicks,
    c.ctr_pct,
    c.cost_per_click,
    COALESCE(a.attributed_orders, 0)                            AS orders,
    COALESCE(a.attributed_customers, 0)                         AS customers,
    COALESCE(a.attributed_new_customers, 0)                     AS new_customers,
    COALESCE(a.attributed_revenue, 0)                           AS revenue,
    COALESCE(a.attributed_profit, 0)                            AS gross_profit,
    COALESCE(a.attributed_aov, 0)                               AS avg_order_value,
    -- ROAS: revenue per unit of spend. >1 means the campaign paid for itself
    -- on a revenue basis; >1/margin means it paid for itself on profit.
    CASE WHEN c.spend > 0
         THEN ROUND(COALESCE(a.attributed_revenue, 0) / c.spend, 2)
         ELSE 0 END                                             AS roas,
    CASE WHEN c.spend > 0
         THEN ROUND(COALESCE(a.attributed_profit, 0) / c.spend, 2)
         ELSE 0 END                                             AS profit_roas,
    ROUND(COALESCE(a.attributed_profit, 0) - c.spend, 2)        AS net_contribution,
    CASE WHEN COALESCE(a.attributed_new_customers, 0) > 0
         THEN ROUND(c.spend / a.attributed_new_customers, 2)
         ELSE NULL END                                          AS cac,
    CASE WHEN COALESCE(a.attributed_orders, 0) > 0
         THEN ROUND(c.spend / a.attributed_orders, 2)
         ELSE NULL END                                          AS cost_per_order,
    CASE WHEN c.clicks > 0
         THEN ROUND(CAST(COALESCE(a.attributed_orders, 0) AS DOUBLE PRECISION) / c.clicks * 100, 3)
         ELSE 0 END                                             AS click_to_order_pct,
    b.baseline_daily_revenue,
    du.window_total_revenue,
    -- Incremental revenue proxy (see header comment).
    ROUND(du.window_total_revenue - b.baseline_daily_revenue * GREATEST(du.window_days, 1), 2)
                                                                AS estimated_incremental_revenue,
    CASE
        WHEN c.spend <= 0                                                     THEN 'No Spend'
        WHEN COALESCE(a.attributed_profit, 0) - c.spend > 0                   THEN 'Profitable'
        WHEN COALESCE(a.attributed_revenue, 0) / NULLIF(c.spend, 0) >= 1.0    THEN 'Revenue Positive'
        ELSE 'Underperforming'
    END                                                         AS verdict
FROM gold.dim_campaign c
LEFT JOIN attributed a  ON a.campaign_key  = c.campaign_key
LEFT JOIN baseline   b  ON b.campaign_key  = c.campaign_key
LEFT JOIN during     du ON du.campaign_key = c.campaign_key
WHERE c.campaign_key <> -1;

-- ---------------------------------------------------------------------------
-- gold.mart_channel_performance - marketing channel roll-up, plus the
-- acquisition channel view (where customers came from, from the CRM side).
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.mart_channel_performance;
CREATE TABLE gold.mart_channel_performance AS
SELECT
    channel,
    COUNT(*)                                                    AS campaigns,
    ROUND(SUM(spend), 2)                                        AS spend,
    ROUND(SUM(budget), 2)                                       AS budget,
    SUM(impressions)                                            AS impressions,
    SUM(clicks)                                                 AS clicks,
    SUM(orders)                                                 AS orders,
    SUM(new_customers)                                          AS new_customers,
    ROUND(SUM(revenue), 2)                                      AS revenue,
    ROUND(SUM(gross_profit), 2)                                 AS gross_profit,
    CASE WHEN SUM(spend) > 0 THEN ROUND(SUM(revenue) / SUM(spend), 2) ELSE 0 END      AS roas,
    CASE WHEN SUM(spend) > 0 THEN ROUND(SUM(gross_profit) / SUM(spend), 2) ELSE 0 END AS profit_roas,
    CASE WHEN SUM(new_customers) > 0 THEN ROUND(SUM(spend) / SUM(new_customers), 2) ELSE NULL END AS cac,
    CASE WHEN SUM(impressions) > 0
         THEN ROUND(CAST(SUM(clicks) AS DOUBLE PRECISION) / SUM(impressions) * 100, 3)
         ELSE 0 END                                             AS ctr_pct,
    ROUND(SUM(gross_profit) - SUM(spend), 2)                    AS net_contribution
FROM gold.mart_campaign_performance
GROUP BY channel;

-- ---------------------------------------------------------------------------
-- gold.mart_acquisition_channel - lifetime value by how the customer arrived.
-- The number that decides where next year's acquisition budget goes.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.mart_acquisition_channel;
CREATE TABLE gold.mart_acquisition_channel AS
SELECT
    acquisition_channel,
    COUNT(*)                                                    AS customers,
    COUNT(*) FILTER (WHERE orders > 0)                          AS activated_customers,
    ROUND(CAST(COUNT(*) FILTER (WHERE orders > 0) AS DOUBLE PRECISION)
          / NULLIF(COUNT(*), 0) * 100, 2)                       AS activation_rate_pct,
    COUNT(*) FILTER (WHERE is_repeat_buyer)                     AS repeat_buyers,
    ROUND(CAST(COUNT(*) FILTER (WHERE is_repeat_buyer) AS DOUBLE PRECISION)
          / NULLIF(COUNT(*) FILTER (WHERE orders > 0), 0) * 100, 2) AS repeat_rate_pct,
    COUNT(*) FILTER (WHERE is_churned)                          AS churned_customers,
    ROUND(SUM(lifetime_revenue), 2)                             AS lifetime_revenue,
    ROUND(SUM(lifetime_profit), 2)                              AS lifetime_profit,
    ROUND(AVG(lifetime_revenue), 2)                             AS avg_lifetime_revenue,
    ROUND(AVG(NULLIF(orders, 0)), 2)                            AS avg_orders_per_buyer,
    ROUND(AVG(NULLIF(avg_order_value, 0)), 2)                   AS avg_order_value,
    ROUND(SUM(lifetime_revenue) / NULLIF(SUM(SUM(lifetime_revenue)) OVER (), 0) * 100, 2)
                                                                AS revenue_share_pct
FROM gold.mart_customer_360
GROUP BY acquisition_channel;
