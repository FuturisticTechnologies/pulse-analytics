-- ===========================================================================
-- gold.analysis_window - the platform's definition of "today".
--
-- Every recency-based metric (RFM, churn, active customers, MTD) anchors to
-- the latest date present in the data, NOT to the wall clock. That single
-- decision is what makes the demo reproducible: the same dataset produces the
-- same segments today and in six months. Switching to a live feed means
-- pointing as_of_date at CURRENT_DATE and nothing else changes.
-- ===========================================================================

DROP TABLE IF EXISTS gold.analysis_window;
CREATE TABLE gold.analysis_window AS
SELECT
    MAX(order_date)                                     AS as_of_date,
    MIN(order_date)                                     AS first_date,
    CAST(MAX(order_date) - MIN(order_date) AS INTEGER) + 1 AS span_days,
    CAST(DATE_TRUNC('month', CAST(MAX(order_date) AS TIMESTAMP)) AS DATE) AS current_month_start,
    MAX(order_date) - 29                                AS trailing_30_start,
    MAX(order_date) - 89                                AS trailing_90_start,
    MAX(order_date) - 364                               AS trailing_365_start
FROM gold.fact_orders;
