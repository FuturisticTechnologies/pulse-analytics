-- ===========================================================================
-- Silver: customers.
--
-- The source deliberately ships dirt (missing emails, 'GOLD  ' style tier
-- values). We repair what is safely repairable, flag the rest, and never drop
-- a customer - a null email is a marketing problem, not a reason to lose the
-- revenue attached to that customer.
-- ===========================================================================

DROP TABLE IF EXISTS silver.customers;
CREATE TABLE silver.customers AS
SELECT
    customer_id,
    TRIM(first_name)                                   AS first_name,
    TRIM(last_name)                                    AS last_name,
    TRIM(first_name) || ' ' || TRIM(last_name)         AS full_name,
    LOWER(TRIM(email))                                 AS email,
    TRIM(phone)                                        AS phone,
    signup_date,
    region_id,
    TRIM(city)                                         AS city,
    TRIM(acquisition_channel)                          AS acquisition_channel,
    birth_year,
    CASE
        WHEN birth_year IS NULL THEN NULL
        ELSE 2025 - birth_year
    END                                                AS age_years,
    CASE
        WHEN birth_year IS NULL           THEN 'Unknown'
        WHEN 2025 - birth_year < 25       THEN '18-24'
        WHEN 2025 - birth_year < 35       THEN '25-34'
        WHEN 2025 - birth_year < 45       THEN '35-44'
        WHEN 2025 - birth_year < 55       THEN '45-54'
        WHEN 2025 - birth_year < 65       THEN '55-64'
        ELSE '65+'
    END                                                AS age_band,
    UPPER(COALESCE(TRIM(gender), 'U'))                 AS gender,
    -- 'GOLD  ' / 'gold' / 'Gold' all collapse to one canonical label.
    CASE UPPER(TRIM(COALESCE(loyalty_tier, '')))
        WHEN 'BRONZE'   THEN 'Bronze'
        WHEN 'SILVER'   THEN 'Silver'
        WHEN 'GOLD'     THEN 'Gold'
        WHEN 'PLATINUM' THEN 'Platinum'
        ELSE 'Bronze'
    END                                                AS loyalty_tier,
    COALESCE(marketing_opt_in, FALSE)                  AS marketing_opt_in,
    -- Quality flags travel with the row so any mart can exclude or report them.
    CASE WHEN email IS NULL OR TRIM(email) = '' THEN TRUE ELSE FALSE END AS is_missing_email,
    CASE WHEN email LIKE '%@%.%' THEN TRUE ELSE FALSE END                AS is_valid_email,
    -- Acquisition cohort: the month the customer first appeared.
    CAST(DATE_TRUNC('month', CAST(signup_date AS TIMESTAMP)) AS DATE)     AS signup_month,
    CAST(EXTRACT(YEAR FROM signup_date) AS INTEGER)                       AS signup_year
FROM (
    SELECT b.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY _loaded_at DESC) AS _rn
    FROM bronze.customers b
    WHERE customer_id IS NOT NULL
) d
WHERE _rn = 1;
