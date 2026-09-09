-- ===========================================================================
-- gold.dim_date - the conformed calendar every fact joins to.
--
-- Generated in SQL (not Python) so the warehouse can be rebuilt from the
-- database alone. Surrogate key is the readable YYYYMMDD integer, which makes
-- fact tables debuggable by eye and partitions cleanly in Synapse/Databricks.
-- ===========================================================================

DROP TABLE IF EXISTS gold.dim_date;
CREATE TABLE gold.dim_date AS
WITH days AS (
    SELECT CAST(g AS DATE) AS d
    FROM generate_series(DATE '2022-01-01', DATE '2027-12-31', INTERVAL '1 day') t(g)
)
SELECT
    CAST(EXTRACT(YEAR  FROM d) AS INTEGER) * 10000
  + CAST(EXTRACT(MONTH FROM d) AS INTEGER) * 100
  + CAST(EXTRACT(DAY   FROM d) AS INTEGER)                        AS date_key,
    d                                                             AS date_value,
    CAST(EXTRACT(YEAR    FROM d) AS INTEGER)                      AS year_number,
    CAST(EXTRACT(QUARTER FROM d) AS INTEGER)                      AS quarter_number,
    'Q' || CAST(CAST(EXTRACT(QUARTER FROM d) AS INTEGER) AS VARCHAR)
        || ' ' || CAST(CAST(EXTRACT(YEAR FROM d) AS INTEGER) AS VARCHAR) AS quarter_label,
    CAST(EXTRACT(MONTH FROM d) AS INTEGER)                        AS month_number,
    CASE CAST(EXTRACT(MONTH FROM d) AS INTEGER)
        WHEN 1 THEN 'Jan' WHEN 2 THEN 'Feb' WHEN 3  THEN 'Mar' WHEN 4  THEN 'Apr'
        WHEN 5 THEN 'May' WHEN 6 THEN 'Jun' WHEN 7  THEN 'Jul' WHEN 8  THEN 'Aug'
        WHEN 9 THEN 'Sep' WHEN 10 THEN 'Oct' WHEN 11 THEN 'Nov' ELSE 'Dec'
    END                                                           AS month_short,
    CAST(DATE_TRUNC('month', CAST(d AS TIMESTAMP)) AS DATE)       AS month_start,
    CAST(DATE_TRUNC('week',  CAST(d AS TIMESTAMP)) AS DATE)       AS week_start,
    CAST(EXTRACT(WEEK FROM d) AS INTEGER)                         AS iso_week,
    CAST(EXTRACT(DOW  FROM d) AS INTEGER)                         AS day_of_week,
    CASE CAST(EXTRACT(DOW FROM d) AS INTEGER)
        WHEN 0 THEN 'Sun' WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue' WHEN 3 THEN 'Wed'
        WHEN 4 THEN 'Thu' WHEN 5 THEN 'Fri' ELSE 'Sat'
    END                                                           AS day_short,
    CAST(EXTRACT(DOY FROM d) AS INTEGER)                          AS day_of_year,
    CASE WHEN CAST(EXTRACT(DOW FROM d) AS INTEGER) IN (0, 6)
         THEN TRUE ELSE FALSE END                                 AS is_weekend,
    -- Retail peak windows the seasonality analysis calls out.
    CASE WHEN CAST(EXTRACT(MONTH FROM d) AS INTEGER) = 11
              AND CAST(EXTRACT(DAY FROM d) AS INTEGER) BETWEEN 24 AND 30
         THEN TRUE ELSE FALSE END                                 AS is_black_friday_window,
    CASE WHEN CAST(EXTRACT(MONTH FROM d) AS INTEGER) = 12
              AND CAST(EXTRACT(DAY FROM d) AS INTEGER) <= 24
         THEN TRUE ELSE FALSE END                                 AS is_holiday_window,
    CASE WHEN CAST(EXTRACT(MONTH FROM d) AS INTEGER) IN (11, 12)
         THEN TRUE ELSE FALSE END                                 AS is_peak_season
FROM days;
