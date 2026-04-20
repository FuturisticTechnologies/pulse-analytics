-- ===========================================================================
-- Silver: FX rates and the country -> currency map.
--
-- The map is a conformed reference table rather than a CASE expression buried
-- in a mart, so adding a market is a data change, not a code change.
-- ===========================================================================

DROP TABLE IF EXISTS silver.currency_by_country;
CREATE TABLE silver.currency_by_country AS
SELECT 'USA'            AS country, 'USD' AS currency_code, 'US Dollar'       AS currency_name UNION ALL
SELECT 'Canada',              'CAD', 'Canadian Dollar'  UNION ALL
SELECT 'Germany',             'EUR', 'Euro'             UNION ALL
SELECT 'United Kingdom',      'GBP', 'Pound Sterling'   UNION ALL
SELECT 'Singapore',           'SGD', 'Singapore Dollar' UNION ALL
SELECT 'Brazil',              'BRL', 'Brazilian Real'   UNION ALL
SELECT 'Mexico',              'MXN', 'Mexican Peso';

DROP TABLE IF EXISTS silver.fx_rates;
CREATE TABLE silver.fx_rates AS
SELECT
    rate_date,
    UPPER(TRIM(base_currency))          AS base_currency,
    UPPER(TRIM(quote_currency))         AS quote_currency,
    rate,
    source
FROM (
    SELECT b.*,
           ROW_NUMBER() OVER (
               PARTITION BY rate_date, base_currency, quote_currency
               ORDER BY _loaded_at DESC
           ) AS _rn
    FROM bronze.fx_rates b
    WHERE rate IS NOT NULL AND rate > 0
) d
WHERE _rn = 1;

-- Latest rate per currency - what the regional mart converts with.
DROP TABLE IF EXISTS silver.fx_rates_latest;
CREATE TABLE silver.fx_rates_latest AS
SELECT quote_currency, base_currency, rate, rate_date, source
FROM (
    SELECT f.*, ROW_NUMBER() OVER (PARTITION BY quote_currency ORDER BY rate_date DESC) AS _rn
    FROM silver.fx_rates f
) t
WHERE _rn = 1;
