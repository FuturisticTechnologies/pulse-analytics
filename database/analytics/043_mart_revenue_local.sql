-- ===========================================================================
-- gold.mart_revenue_local - regional revenue restated in local currency.
--
-- Consumes the external FX feed. Every row carries the rate and the rate date
-- used, because a converted number without its rate is unauditable - and the
-- first question a finance reviewer asks is "at what rate?".
-- ===========================================================================

DROP TABLE IF EXISTS gold.mart_revenue_local;
CREATE TABLE gold.mart_revenue_local AS
SELECT
    r.region_key,
    r.region_id,
    r.region_name,
    r.country,
    COALESCE(cc.currency_code, 'USD')                           AS currency_code,
    COALESCE(cc.currency_name, 'US Dollar')                     AS currency_name,
    r.revenue                                                   AS revenue_usd,
    r.gross_profit                                              AS gross_profit_usd,
    COALESCE(fx.rate, 1.0)                                      AS fx_rate,
    fx.rate_date                                                AS fx_rate_date,
    COALESCE(fx.source, 'identity')                             AS fx_source,
    ROUND(r.revenue      * COALESCE(fx.rate, 1.0), 2)           AS revenue_local,
    ROUND(r.gross_profit * COALESCE(fx.rate, 1.0), 2)           AS gross_profit_local,
    ROUND(r.avg_order_value * COALESCE(fx.rate, 1.0), 2)        AS avg_order_value_local
FROM gold.mart_regional_performance r
LEFT JOIN silver.currency_by_country cc ON cc.country = r.country
LEFT JOIN silver.fx_rates_latest fx     ON fx.quote_currency = cc.currency_code;
