-- ===========================================================================
-- PulseAnalytics - schema layout (medallion architecture)
--
--   bronze  raw landing zone. Source columns, source types, nothing dropped.
--   silver  cleaned, typed, de-duplicated, conformed business entities.
--   gold    star schema + pre-aggregated marts that dashboards read.
--   ops     pipeline metadata: run log, data-quality results, stream state.
--
-- Portable across DuckDB (local/CI) and PostgreSQL (docker/production).
-- ===========================================================================

CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS ops;
