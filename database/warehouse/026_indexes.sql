-- ===========================================================================
-- Indexes on the join and filter columns every mart and dashboard uses.
--
-- DuckDB keeps zone maps automatically and needs far fewer of these than
-- Postgres, but the same script runs on both so the production target gets the
-- indexes it actually needs.
-- ===========================================================================

CREATE INDEX IF NOT EXISTS ix_fact_sales_date      ON gold.fact_sales (order_date_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_customer  ON gold.fact_sales (customer_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_product   ON gold.fact_sales (product_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_region    ON gold.fact_sales (region_key);
CREATE INDEX IF NOT EXISTS ix_fact_sales_campaign  ON gold.fact_sales (campaign_key);

CREATE INDEX IF NOT EXISTS ix_fact_orders_date     ON gold.fact_orders (order_date_key);
CREATE INDEX IF NOT EXISTS ix_fact_orders_customer ON gold.fact_orders (customer_key);

CREATE INDEX IF NOT EXISTS ix_fact_payments_date   ON gold.fact_payments (payment_date_key);
CREATE INDEX IF NOT EXISTS ix_fact_payments_order  ON gold.fact_payments (order_id);

CREATE INDEX IF NOT EXISTS ix_fact_inventory_date  ON gold.fact_inventory (snapshot_date_key);
CREATE INDEX IF NOT EXISTS ix_fact_inventory_prod  ON gold.fact_inventory (product_key);

CREATE INDEX IF NOT EXISTS ix_fact_events_date     ON gold.fact_customer_events (event_date_key);
CREATE INDEX IF NOT EXISTS ix_fact_events_customer ON gold.fact_customer_events (customer_key);

CREATE INDEX IF NOT EXISTS ix_dim_date_value       ON gold.dim_date (date_value);
CREATE INDEX IF NOT EXISTS ix_dim_customer_natural ON gold.dim_customer (customer_id);
CREATE INDEX IF NOT EXISTS ix_dim_product_natural  ON gold.dim_product (product_id);

CREATE INDEX IF NOT EXISTS ix_stream_events_ts     ON ops.stream_events (event_ts);
CREATE INDEX IF NOT EXISTS ix_stream_events_topic  ON ops.stream_events (topic);
