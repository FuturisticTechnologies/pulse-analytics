-- ===========================================================================
-- ops: everything the platform knows about itself.
--
-- These tables are what turns a pile of scripts into an operable pipeline -
-- they answer "did it run", "how long did it take", "what broke", and
-- "is the data safe to publish to the executive dashboard".
--
-- IMPORTANT: unlike bronze, these are CREATE TABLE IF NOT EXISTS and are NOT
-- dropped by a full refresh. They are append-only histories, and the whole
-- point of a run log is that it outlives the run. Dropping ops.stream_events
-- on every batch build would also delete the real-time landing zone every time
-- someone rebuilt the warehouse - a batch job silently destroying the
-- streaming layer is exactly the kind of coupling that causes a 3am page.
--
-- To rebuild these deliberately (a schema change):
--     DROP SCHEMA ops CASCADE;  then re-run: python -m etl.pipeline --stage init
-- ===========================================================================

CREATE TABLE IF NOT EXISTS ops.pipeline_runs (
    run_id          VARCHAR(40),
    pipeline        VARCHAR(60),
    stage           VARCHAR(60),
    status          VARCHAR(20),     -- running | success | failed
    started_at      TIMESTAMP,
    finished_at     TIMESTAMP,
    duration_sec    DOUBLE PRECISION,
    rows_in         BIGINT,
    rows_out        BIGINT,
    message         VARCHAR(1000)
);

CREATE TABLE IF NOT EXISTS ops.data_quality_results (
    run_id          VARCHAR(40),
    checked_at      TIMESTAMP,
    layer           VARCHAR(20),     -- bronze | silver | gold
    table_name      VARCHAR(80),
    check_name      VARCHAR(120),
    dimension       VARCHAR(30),     -- completeness | validity | uniqueness |
                                     -- consistency | timeliness | accuracy
    severity        VARCHAR(20),     -- error | warning | info
    status          VARCHAR(10),     -- pass | fail
    observed_value  DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,
    failed_rows     BIGINT,
    total_rows      BIGINT,
    details         VARCHAR(1000)
);

-- Real-time landing zone. The stream consumer appends here; the realtime KPI
-- views read from it, so streaming and batch share one query surface.
CREATE TABLE IF NOT EXISTS ops.stream_events (
    event_id        VARCHAR(64),
    topic           VARCHAR(60),
    event_type      VARCHAR(40),
    event_ts        TIMESTAMP,
    ingested_at     TIMESTAMP,
    customer_id     BIGINT,
    order_id        BIGINT,
    product_id      BIGINT,
    store_id        INTEGER,
    region_id       INTEGER,
    channel         VARCHAR(40),
    status          VARCHAR(30),
    amount          DOUBLE PRECISION,
    quantity        INTEGER,
    payload         VARCHAR(4000)    -- original JSON, kept for replay/debug
);

-- Rolling minute-level aggregates written by the stream processor. Keeping
-- them in a table (not just memory) means the dashboard survives a restart.
CREATE TABLE IF NOT EXISTS ops.realtime_kpis (
    window_start        TIMESTAMP,
    window_end          TIMESTAMP,
    orders              BIGINT,
    revenue             DOUBLE PRECISION,
    avg_order_value     DOUBLE PRECISION,
    payment_attempts    BIGINT,
    payment_failures    BIGINT,
    failure_rate_pct    DOUBLE PRECISION,
    active_sessions     BIGINT,
    stockout_alerts     BIGINT,
    computed_at         TIMESTAMP
);

-- Watermarks let incremental loads resume exactly where they stopped.
CREATE TABLE IF NOT EXISTS ops.load_watermarks (
    table_name      VARCHAR(80),
    watermark_col   VARCHAR(60),
    watermark_value TIMESTAMP,
    updated_at      TIMESTAMP
);
