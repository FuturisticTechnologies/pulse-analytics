-- ===========================================================================
-- Silver: reference entities (regions, stores, products, campaigns).
--
-- Rules applied here and nowhere else:
--   * trim and case-normalise every free-text categorical,
--   * de-duplicate on the natural key, keeping the last-loaded row,
--   * derive attributes the whole platform needs (margin %, price band).
-- ===========================================================================

DROP TABLE IF EXISTS silver.regions;
CREATE TABLE silver.regions AS
SELECT
    region_id,
    TRIM(region_name)                       AS region_name,
    TRIM(country)                           AS country,
    TRIM(timezone)                          AS timezone,
    CASE
        WHEN TRIM(country) IN ('USA', 'Canada')            THEN 'Americas'
        WHEN TRIM(country) IN ('Brazil', 'Mexico')         THEN 'Americas'
        WHEN TRIM(country) IN ('Germany', 'United Kingdom') THEN 'EMEA'
        ELSE 'APAC'
    END                                     AS super_region
FROM bronze.regions
WHERE region_id IS NOT NULL;

DROP TABLE IF EXISTS silver.stores;
CREATE TABLE silver.stores AS
SELECT
    store_id,
    TRIM(store_name)                        AS store_name,
    TRIM(store_type)                        AS store_type,
    region_id,
    TRIM(city)                              AS city,
    TRIM(country)                           AS country,
    opened_date,
    floor_sqm,
    CASE WHEN TRIM(store_type) = 'Online' THEN TRUE ELSE FALSE END AS is_digital
FROM (
    SELECT b.*, ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY _loaded_at DESC) AS _rn
    FROM bronze.stores b
    WHERE store_id IS NOT NULL
) d
WHERE _rn = 1;

DROP TABLE IF EXISTS silver.products;
CREATE TABLE silver.products AS
SELECT
    product_id,
    UPPER(TRIM(sku))                        AS sku,
    TRIM(product_name)                      AS product_name,
    TRIM(category)                          AS category,
    TRIM(subcategory)                       AS subcategory,
    TRIM(brand)                             AS brand,
    unit_price,
    unit_cost,
    ROUND(unit_price - unit_cost, 2)        AS unit_margin,
    CASE
        WHEN unit_price > 0 THEN ROUND((unit_price - unit_cost) / unit_price * 100, 2)
        ELSE 0
    END                                     AS margin_pct,
    CASE
        WHEN unit_price <  25  THEN 'Budget'
        WHEN unit_price < 100  THEN 'Mid'
        WHEN unit_price < 400  THEN 'Premium'
        ELSE 'Luxury'
    END                                     AS price_band,
    launch_date,
    COALESCE(is_active, TRUE)               AS is_active,
    weight_kg
FROM (
    SELECT b.*, ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY _loaded_at DESC) AS _rn
    FROM bronze.products b
    WHERE product_id IS NOT NULL AND unit_price IS NOT NULL
) d
WHERE _rn = 1;

DROP TABLE IF EXISTS silver.campaigns;
CREATE TABLE silver.campaigns AS
SELECT
    campaign_id,
    TRIM(campaign_name)                     AS campaign_name,
    TRIM(channel)                           AS channel,
    TRIM(objective)                         AS objective,
    start_date,
    end_date,
    (end_date - start_date) + 1             AS duration_days,
    budget,
    spend,
    GREATEST(impressions, 0)                AS impressions,
    GREATEST(clicks, 0)                     AS clicks,
    CASE WHEN impressions > 0
         THEN ROUND(CAST(clicks AS DOUBLE PRECISION) / impressions * 100, 4)
         ELSE 0 END                         AS ctr_pct,
    CASE WHEN clicks > 0
         THEN ROUND(spend / clicks, 4)
         ELSE 0 END                         AS cost_per_click,
    CASE WHEN budget > 0
         THEN ROUND(spend / budget * 100, 2)
         ELSE 0 END                         AS budget_utilisation_pct,
    TRIM(target_segment)                    AS target_segment
FROM bronze.campaigns
WHERE campaign_id IS NOT NULL;
