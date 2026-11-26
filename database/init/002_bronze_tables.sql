-- ===========================================================================
-- Bronze: landing tables mirroring the source extracts one-for-one.
--
-- Deliberately permissive - no NOT NULL, no foreign keys, wide numeric types.
-- Bronze must never reject a row: if the source system sends garbage we want
-- it landed and *counted* by the data-quality layer, not silently lost.
-- ===========================================================================

DROP TABLE IF EXISTS bronze.regions;
CREATE TABLE bronze.regions (
    region_id       INTEGER,
    region_name     VARCHAR(80),
    country         VARCHAR(80),
    timezone        VARCHAR(64),
    _loaded_at      TIMESTAMP,
    _source_file    VARCHAR(200)
);

DROP TABLE IF EXISTS bronze.stores;
CREATE TABLE bronze.stores (
    store_id        INTEGER,
    store_name      VARCHAR(120),
    store_type      VARCHAR(40),
    region_id       INTEGER,
    city            VARCHAR(80),
    country         VARCHAR(80),
    opened_date     DATE,
    floor_sqm       DOUBLE PRECISION,
    _loaded_at      TIMESTAMP,
    _source_file    VARCHAR(200)
);

DROP TABLE IF EXISTS bronze.products;
CREATE TABLE bronze.products (
    product_id      INTEGER,
    sku             VARCHAR(40),
    product_name    VARCHAR(160),
    category        VARCHAR(60),
    subcategory     VARCHAR(60),
    brand           VARCHAR(60),
    unit_price      DOUBLE PRECISION,
    unit_cost       DOUBLE PRECISION,
    launch_date     DATE,
    is_active       BOOLEAN,
    weight_kg       DOUBLE PRECISION,
    _loaded_at      TIMESTAMP,
    _source_file    VARCHAR(200)
);

DROP TABLE IF EXISTS bronze.customers;
CREATE TABLE bronze.customers (
    customer_id         INTEGER,
    first_name          VARCHAR(60),
    last_name           VARCHAR(60),
    email               VARCHAR(160),
    phone               VARCHAR(40),
    signup_date         DATE,
    region_id           INTEGER,
    city                VARCHAR(80),
    acquisition_channel VARCHAR(60),
    birth_year          INTEGER,
    gender              VARCHAR(10),
    loyalty_tier        VARCHAR(40),   -- arrives dirty: 'GOLD  ', 'gold', 'Gold'
    marketing_opt_in    BOOLEAN,
    _loaded_at          TIMESTAMP,
    _source_file        VARCHAR(200)
);

DROP TABLE IF EXISTS bronze.campaigns;
CREATE TABLE bronze.campaigns (
    campaign_id     INTEGER,
    campaign_name   VARCHAR(160),
    channel         VARCHAR(60),
    objective       VARCHAR(40),
    start_date      DATE,
    end_date        DATE,
    budget          DOUBLE PRECISION,
    spend           DOUBLE PRECISION,
    impressions     BIGINT,
    clicks          BIGINT,
    target_segment  VARCHAR(60),
    _loaded_at      TIMESTAMP,
    _source_file    VARCHAR(200)
);

DROP TABLE IF EXISTS bronze.orders;
CREATE TABLE bronze.orders (
    order_id        BIGINT,
    customer_id     INTEGER,
    store_id        INTEGER,
    order_ts        TIMESTAMP,
    order_date      DATE,
    channel         VARCHAR(40),
    status          VARCHAR(20),
    status_reason   VARCHAR(60),        -- why cancelled/returned; often blank
    currency        VARCHAR(8),
    campaign_id     DOUBLE PRECISION,   -- nullable FK arrives as float from CSV
    item_count      INTEGER,
    gross_amount    DOUBLE PRECISION,
    discount_amount DOUBLE PRECISION,
    shipping_amount DOUBLE PRECISION,
    tax_amount      DOUBLE PRECISION,
    net_amount      DOUBLE PRECISION,
    total_amount    DOUBLE PRECISION,
    cost_amount     DOUBLE PRECISION,
    _loaded_at      TIMESTAMP,
    _source_file    VARCHAR(200)
);

DROP TABLE IF EXISTS bronze.order_items;
CREATE TABLE bronze.order_items (
    order_item_id   BIGINT,
    order_id        BIGINT,
    product_id      INTEGER,
    quantity        INTEGER,            -- occasionally negative in the source
    unit_price      DOUBLE PRECISION,
    unit_cost       DOUBLE PRECISION,
    discount_amount DOUBLE PRECISION,
    gross_amount    DOUBLE PRECISION,
    line_amount     DOUBLE PRECISION,
    line_cost       DOUBLE PRECISION,
    _loaded_at      TIMESTAMP,
    _source_file    VARCHAR(200)
);

DROP TABLE IF EXISTS bronze.payments;
CREATE TABLE bronze.payments (
    payment_id      BIGINT,
    order_id        BIGINT,
    payment_method  VARCHAR(40),
    payment_ts      TIMESTAMP,
    amount          DOUBLE PRECISION,
    status          VARCHAR(20),
    failure_reason  VARCHAR(60),
    attempt_number  INTEGER,
    _loaded_at      TIMESTAMP,
    _source_file    VARCHAR(200)
);

DROP TABLE IF EXISTS bronze.inventory_snapshots;
CREATE TABLE bronze.inventory_snapshots (
    inventory_id    BIGINT,
    snapshot_date   DATE,
    product_id      INTEGER,
    on_hand_units   INTEGER,
    reorder_point   INTEGER,
    units_sold      INTEGER,
    restock_units   INTEGER,
    is_stockout     BOOLEAN,
    _loaded_at      TIMESTAMP,
    _source_file    VARCHAR(200)
);

DROP TABLE IF EXISTS bronze.customer_events;
CREATE TABLE bronze.customer_events (
    event_id            BIGINT,
    customer_id         BIGINT,         -- orphan ids appear here on purpose
    event_ts            TIMESTAMP,
    event_type          VARCHAR(40),
    session_id          VARCHAR(40),
    device              VARCHAR(20),
    product_id          DOUBLE PRECISION,
    page_url            VARCHAR(200),
    duration_seconds    DOUBLE PRECISION,
    _loaded_at          TIMESTAMP,
    _source_file        VARCHAR(200)
);

-- ---------------------------------------------------------------------------
-- External API feed. Not part of the transactional source system: this is
-- pulled by etl/extract/api_source.py from a public FX endpoint (with a
-- deterministic offline fallback so the pipeline never depends on the network
-- to succeed). It is what makes the "External API" arm of the architecture
-- real rather than decorative - regional revenue is reported in local currency
-- using these rates.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS bronze.fx_rates;
CREATE TABLE bronze.fx_rates (
    rate_date       DATE,
    base_currency   VARCHAR(8),
    quote_currency  VARCHAR(8),
    rate            DOUBLE PRECISION,
    source          VARCHAR(40),
    _loaded_at      TIMESTAMP,
    _source_file    VARCHAR(200)
);
