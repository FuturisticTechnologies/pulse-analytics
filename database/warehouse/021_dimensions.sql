-- ===========================================================================
-- gold dimensions.
--
-- Kimball surrogate keys (dense integers assigned here) plus the natural key,
-- which stays on the row so a human can trace a fact back to the source system
-- without a join. Every dimension carries a -1 "Unknown" member so facts never
-- need an outer join and counts never silently drop rows.
--
-- Change tracking: these are Type 1 (overwrite). The one attribute with real
-- business drift - loyalty tier - is snapshotted in gold.dim_customer_history
-- as Type 2, which is where "revenue by the tier the customer held at the time
-- of purchase" is answered.
-- ===========================================================================

-- ------------------------------------------------------------------ region
DROP TABLE IF EXISTS gold.dim_region;
CREATE TABLE gold.dim_region AS
SELECT -1 AS region_key, -1 AS region_id, 'Unknown' AS region_name,
       'Unknown' AS country, 'UTC' AS timezone, 'Unknown' AS super_region
UNION ALL
SELECT
    CAST(ROW_NUMBER() OVER (ORDER BY region_id) AS INTEGER) AS region_key,
    region_id, region_name, country, timezone, super_region
FROM silver.regions;

-- ------------------------------------------------------------------- store
DROP TABLE IF EXISTS gold.dim_store;
CREATE TABLE gold.dim_store AS
SELECT -1 AS store_key, -1 AS store_id, 'Unknown' AS store_name,
       'Unknown' AS store_type, -1 AS region_key, 'Unknown' AS city,
       'Unknown' AS country, CAST(NULL AS DATE) AS opened_date,
       CAST(NULL AS DOUBLE PRECISION) AS floor_sqm, FALSE AS is_digital
UNION ALL
SELECT
    CAST(ROW_NUMBER() OVER (ORDER BY s.store_id) AS INTEGER) AS store_key,
    s.store_id,
    s.store_name,
    s.store_type,
    COALESCE(r.region_key, -1) AS region_key,
    s.city,
    s.country,
    s.opened_date,
    s.floor_sqm,
    s.is_digital
FROM silver.stores s
LEFT JOIN gold.dim_region r ON r.region_id = s.region_id;

-- ----------------------------------------------------------------- product
DROP TABLE IF EXISTS gold.dim_product;
CREATE TABLE gold.dim_product AS
SELECT -1 AS product_key, -1 AS product_id, 'UNKNOWN' AS sku,
       'Unknown' AS product_name, 'Unknown' AS category, 'Unknown' AS subcategory,
       'Unknown' AS brand,
       CAST(0 AS DOUBLE PRECISION) AS unit_price, CAST(0 AS DOUBLE PRECISION) AS unit_cost,
       CAST(0 AS DOUBLE PRECISION) AS unit_margin, CAST(0 AS DOUBLE PRECISION) AS margin_pct,
       'Unknown' AS price_band, CAST(NULL AS DATE) AS launch_date,
       FALSE AS is_active, CAST(NULL AS DOUBLE PRECISION) AS weight_kg
UNION ALL
SELECT
    CAST(ROW_NUMBER() OVER (ORDER BY product_id) AS INTEGER) AS product_key,
    product_id, sku, product_name, category, subcategory, brand,
    unit_price, unit_cost, unit_margin, margin_pct, price_band,
    launch_date, is_active, weight_kg
FROM silver.products;

-- ---------------------------------------------------------------- customer
DROP TABLE IF EXISTS gold.dim_customer;
CREATE TABLE gold.dim_customer AS
SELECT -1 AS customer_key, -1 AS customer_id, 'Unknown' AS full_name,
       CAST(NULL AS VARCHAR) AS email, CAST(NULL AS DATE) AS signup_date,
       CAST(NULL AS DATE) AS signup_month, -1 AS region_key, 'Unknown' AS city,
       'Unknown' AS acquisition_channel, 'Unknown' AS age_band, 'U' AS gender,
       'Unknown' AS loyalty_tier, FALSE AS marketing_opt_in, FALSE AS is_missing_email
UNION ALL
SELECT
    CAST(ROW_NUMBER() OVER (ORDER BY c.customer_id) AS INTEGER) AS customer_key,
    c.customer_id,
    c.full_name,
    c.email,
    c.signup_date,
    c.signup_month,
    COALESCE(r.region_key, -1) AS region_key,
    c.city,
    c.acquisition_channel,
    c.age_band,
    c.gender,
    c.loyalty_tier,
    c.marketing_opt_in,
    c.is_missing_email
FROM silver.customers c
LEFT JOIN gold.dim_region r ON r.region_id = c.region_id;

-- ---------------------------------------------------------------- campaign
DROP TABLE IF EXISTS gold.dim_campaign;
CREATE TABLE gold.dim_campaign AS
SELECT -1 AS campaign_key, -1 AS campaign_id, 'No Campaign' AS campaign_name,
       'None' AS channel, 'None' AS objective,
       CAST(NULL AS DATE) AS start_date, CAST(NULL AS DATE) AS end_date,
       0 AS duration_days,
       CAST(0 AS DOUBLE PRECISION) AS budget, CAST(0 AS DOUBLE PRECISION) AS spend,
       CAST(0 AS BIGINT) AS impressions, CAST(0 AS BIGINT) AS clicks,
       CAST(0 AS DOUBLE PRECISION) AS ctr_pct, CAST(0 AS DOUBLE PRECISION) AS cost_per_click,
       'None' AS target_segment
UNION ALL
SELECT
    CAST(ROW_NUMBER() OVER (ORDER BY campaign_id) AS INTEGER) AS campaign_key,
    campaign_id, campaign_name, channel, objective, start_date, end_date,
    CAST(duration_days AS INTEGER), budget, spend,
    CAST(impressions AS BIGINT), CAST(clicks AS BIGINT),
    ctr_pct, cost_per_click, target_segment
FROM silver.campaigns;

-- ---------------------------------------------------------- payment method
DROP TABLE IF EXISTS gold.dim_payment_method;
CREATE TABLE gold.dim_payment_method AS
SELECT
    CAST(ROW_NUMBER() OVER (ORDER BY payment_method) AS INTEGER) AS payment_method_key,
    payment_method,
    CASE
        WHEN payment_method IN ('Credit Card', 'Debit Card') THEN 'Card'
        WHEN payment_method IN ('PayPal', 'Apple Pay')       THEN 'Wallet'
        WHEN payment_method = 'Bank Transfer'                THEN 'Bank'
        ELSE 'Other'
    END AS method_family
FROM (SELECT DISTINCT payment_method FROM silver.payments WHERE payment_method IS NOT NULL) m;

-- --------------------------------------------- customer history (SCD Type 2)
-- One row per customer per loyalty tier they have held. The generator ships a
-- single tier per customer, so today this is one row each - but the shape and
-- the load logic are Type 2, so the moment a tier change lands the history is
-- correct without a model change.
DROP TABLE IF EXISTS gold.dim_customer_history;
CREATE TABLE gold.dim_customer_history AS
SELECT
    CAST(ROW_NUMBER() OVER (ORDER BY customer_id, signup_date) AS INTEGER) AS customer_history_key,
    customer_id,
    loyalty_tier,
    acquisition_channel,
    signup_date                     AS valid_from,
    CAST(DATE '9999-12-31' AS DATE) AS valid_to,
    TRUE                            AS is_current,
    1                               AS version_number
FROM silver.customers;
