-- ===========================================================================
-- Reporting views.
--
-- Views, not tables, for two reasons:
--   * the real-time ones must reflect ops.stream_events the instant the
--     consumer writes a row - materialising them would add exactly the latency
--     the streaming layer exists to remove;
--   * the flattened star view is what Power BI imports, and keeping it a view
--     means the semantic model never drifts from the warehouse.
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- Flattened sales view - one wide, self-describing table for BI tools that
-- would rather not model a star themselves.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.v_sales_flat AS
SELECT
    s.sales_key,
    s.order_id,
    s.order_date,
    s.order_ts,
    d.year_number,
    d.quarter_label,
    d.month_start,
    d.month_short,
    d.week_start,
    d.day_short,
    d.is_weekend,
    d.is_peak_season,
    c.customer_id,
    c.full_name            AS customer_name,
    c.loyalty_tier,
    c.acquisition_channel,
    c.age_band,
    p.product_id,
    p.sku,
    p.product_name,
    p.category,
    p.subcategory,
    p.brand,
    p.price_band,
    st.store_name,
    st.store_type,
    r.region_name,
    r.country,
    r.super_region,
    cp.campaign_name,
    cp.channel             AS marketing_channel,
    s.order_channel,
    s.order_status,
    s.quantity,
    s.unit_price,
    s.net_amount           AS revenue,
    s.discount_amount,
    s.cost_amount,
    s.gross_profit,
    s.margin_pct,
    s.is_revenue
FROM gold.fact_sales s
JOIN gold.dim_date     d  ON d.date_key     = s.order_date_key
JOIN gold.dim_customer c  ON c.customer_key = s.customer_key
JOIN gold.dim_product  p  ON p.product_key  = s.product_key
JOIN gold.dim_store    st ON st.store_key   = s.store_key
JOIN gold.dim_region   r  ON r.region_key   = s.region_key
JOIN gold.dim_campaign cp ON cp.campaign_key = s.campaign_key;

-- ---------------------------------------------------------------------------
-- Real-time views over the streaming landing table.
-- ---------------------------------------------------------------------------

-- Live trading in the last 60 minutes of stream time (stream time, not wall
-- time, so a replayed stream still lights the dashboard up).
CREATE OR REPLACE VIEW gold.v_realtime_orders AS
SELECT
    CAST(DATE_TRUNC('minute', event_ts) AS TIMESTAMP)       AS minute_bucket,
    COUNT(*)                                                AS orders,
    ROUND(SUM(amount), 2)                                   AS revenue,
    ROUND(AVG(amount), 2)                                   AS avg_order_value,
    COUNT(DISTINCT customer_id)                             AS customers
FROM ops.stream_events
WHERE topic = 'pulse.orders'
GROUP BY 1;

CREATE OR REPLACE VIEW gold.v_realtime_payments AS
SELECT
    CAST(DATE_TRUNC('minute', event_ts) AS TIMESTAMP)       AS minute_bucket,
    COUNT(*)                                                AS attempts,
    COUNT(*) FILTER (WHERE status = 'captured')             AS captured,
    COUNT(*) FILTER (WHERE status = 'failed')               AS failed,
    ROUND(CAST(COUNT(*) FILTER (WHERE status = 'failed') AS DOUBLE PRECISION)
          / NULLIF(COUNT(*), 0) * 100, 2)                   AS failure_rate_pct,
    ROUND(SUM(amount) FILTER (WHERE status = 'failed'), 2)  AS amount_at_risk
FROM ops.stream_events
WHERE topic = 'pulse.payments'
GROUP BY 1;

CREATE OR REPLACE VIEW gold.v_realtime_activity AS
SELECT
    CAST(DATE_TRUNC('minute', event_ts) AS TIMESTAMP)       AS minute_bucket,
    event_type,
    COUNT(*)                                                AS events,
    COUNT(DISTINCT customer_id)                             AS customers
FROM ops.stream_events
WHERE topic = 'pulse.customer_activity'
GROUP BY 1, 2;

CREATE OR REPLACE VIEW gold.v_realtime_inventory_alerts AS
SELECT
    event_ts,
    product_id,
    status                                                  AS alert_type,
    quantity                                                AS on_hand_units,
    store_id
FROM ops.stream_events
WHERE topic = 'pulse.inventory'
  AND status IN ('stockout', 'low_stock');

-- ---------------------------------------------------------------------------
-- Data-quality scoreboard: the traffic light on every dashboard header.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW ops.v_data_quality_summary AS
SELECT
    run_id,
    MAX(checked_at)                                         AS checked_at,
    COUNT(*)                                                AS checks_run,
    COUNT(*) FILTER (WHERE status = 'pass')                 AS checks_passed,
    COUNT(*) FILTER (WHERE status = 'fail')                 AS checks_failed,
    COUNT(*) FILTER (WHERE status = 'fail' AND severity = 'error')   AS errors,
    COUNT(*) FILTER (WHERE status = 'fail' AND severity = 'warning') AS warnings,
    ROUND(CAST(COUNT(*) FILTER (WHERE status = 'pass') AS DOUBLE PRECISION)
          / NULLIF(COUNT(*), 0) * 100, 1)                   AS pass_rate_pct
FROM ops.data_quality_results
GROUP BY run_id;

-- ---------------------------------------------------------------------------
-- Pipeline health: last run of every stage, newest first.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW ops.v_pipeline_health AS
SELECT
    pipeline,
    stage,
    status,
    started_at,
    finished_at,
    duration_sec,
    rows_in,
    rows_out,
    message
FROM ops.pipeline_runs;
