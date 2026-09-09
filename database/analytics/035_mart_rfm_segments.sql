-- ===========================================================================
-- gold.mart_rfm_segments - RFM scoring and the 11 standard behavioural segments.
--
--   R  recency   - days since last order, LOW is good  -> reversed quintile
--   F  frequency - lifetime completed orders           -> quintile
--   M  monetary  - lifetime net revenue                -> quintile
--
-- Quintiles (NTILE(5)) rather than fixed thresholds, because absolute cut-offs
-- stop being meaningful the moment the business grows. Customers who have
-- never ordered get no score and land in 'Prospect' - scoring them would drag
-- every quintile boundary towards zero.
--
-- Segment names follow the widely used RFM grid so the output is immediately
-- legible to a marketing team without a glossary.
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_rfm_segments;
CREATE TABLE gold.mart_rfm_segments AS
WITH buyers AS (
    SELECT
        customer_key,
        customer_id,
        full_name,
        email,
        loyalty_tier,
        acquisition_channel,
        region_key,
        recency_days,
        orders                  AS frequency,
        lifetime_revenue        AS monetary,
        avg_order_value,
        tenure_days,
        lifecycle_status,
        marketing_opt_in
    FROM gold.mart_customer_360
    WHERE orders > 0
),
scored AS (
    SELECT
        b.*,
        -- 5 = most recent. NTILE ascending on recency_days puts the freshest
        -- customers in tile 1, so the score is inverted.
        CAST(6 - NTILE(5) OVER (ORDER BY recency_days ASC) AS INTEGER)  AS r_score,
        CAST(NTILE(5) OVER (ORDER BY frequency ASC) AS INTEGER)         AS f_score,
        CAST(NTILE(5) OVER (ORDER BY monetary  ASC) AS INTEGER)         AS m_score
    FROM buyers b
),
labelled AS (
    SELECT
        s.*,
        CAST(s.r_score AS VARCHAR) || CAST(s.f_score AS VARCHAR)
            || CAST(s.m_score AS VARCHAR)                               AS rfm_cell,
        ROUND((s.r_score + s.f_score + s.m_score) / 3.0, 2)             AS rfm_score,
        CASE
            WHEN s.r_score >= 4 AND s.f_score >= 4 AND s.m_score >= 4 THEN 'Champions'
            WHEN s.r_score >= 3 AND s.f_score >= 4                    THEN 'Loyal Customers'
            WHEN s.r_score >= 4 AND s.f_score <= 2 AND s.m_score >= 3 THEN 'Big Spenders'
            WHEN s.r_score >= 4 AND s.f_score <= 2                    THEN 'New Customers'
            WHEN s.r_score >= 3 AND s.f_score = 3                     THEN 'Potential Loyalists'
            WHEN s.r_score = 3 AND s.f_score <= 2                     THEN 'Promising'
            WHEN s.r_score = 2 AND s.f_score >= 3                     THEN 'At Risk'
            WHEN s.r_score = 2 AND s.m_score >= 4                     THEN 'Cannot Lose Them'
            WHEN s.r_score = 2                                        THEN 'Needs Attention'
            WHEN s.r_score = 1 AND s.f_score >= 3                     THEN 'Hibernating'
            ELSE 'Lost'
        END                                                             AS rfm_segment
    FROM scored s
)
SELECT
    l.*,
    -- Recommended next action. Putting this in the warehouse (not in a slide)
    -- means the CRM export and the dashboard cannot disagree about it.
    CASE l.rfm_segment
        WHEN 'Champions'           THEN 'Reward: early access, referral ask'
        WHEN 'Loyal Customers'     THEN 'Upsell adjacent categories'
        WHEN 'Big Spenders'        THEN 'Personal outreach, premium bundles'
        WHEN 'New Customers'       THEN 'Onboarding series, second-purchase nudge'
        WHEN 'Potential Loyalists' THEN 'Loyalty enrolment offer'
        WHEN 'Promising'           THEN 'Category education, light discount'
        WHEN 'At Risk'             THEN 'Win-back offer within 14 days'
        WHEN 'Cannot Lose Them'    THEN 'High-touch save call, service review'
        WHEN 'Needs Attention'     THEN 'Reactivation email with incentive'
        WHEN 'Hibernating'         THEN 'Low-cost reactivation, then suppress'
        ELSE 'Suppress from paid media'
    END                                                                 AS recommended_action,
    CASE
        WHEN l.rfm_segment IN ('Champions', 'Loyal Customers', 'Big Spenders') THEN 'High'
        WHEN l.rfm_segment IN ('At Risk', 'Cannot Lose Them')                  THEN 'Urgent'
        WHEN l.rfm_segment IN ('Lost', 'Hibernating')                          THEN 'Low'
        ELSE 'Medium'
    END                                                                 AS priority
FROM labelled l;

-- ---------------------------------------------------------------------------
-- Segment-level roll-up: the shape marketing actually briefs against.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS gold.mart_rfm_summary;
CREATE TABLE gold.mart_rfm_summary AS
SELECT
    rfm_segment,
    priority,
    COUNT(*)                                                            AS customers,
    ROUND(AVG(recency_days), 1)                                         AS avg_recency_days,
    ROUND(AVG(frequency), 2)                                            AS avg_orders,
    ROUND(AVG(monetary), 2)                                             AS avg_lifetime_revenue,
    ROUND(AVG(avg_order_value), 2)                                      AS avg_order_value,
    ROUND(SUM(monetary), 2)                                             AS segment_revenue,
    ROUND(SUM(monetary) / NULLIF(SUM(SUM(monetary)) OVER (), 0) * 100, 2) AS revenue_share_pct,
    ROUND(CAST(COUNT(*) AS DOUBLE PRECISION)
          / NULLIF(SUM(COUNT(*)) OVER (), 0) * 100, 2)                  AS customer_share_pct,
    COUNT(*) FILTER (WHERE marketing_opt_in)                            AS contactable_customers
FROM gold.mart_rfm_segments
GROUP BY rfm_segment, priority;
