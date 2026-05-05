"""The ETL machinery: configuration, the database facade, extract, load, and the
pipeline orchestration around them.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from etl.extract import api_source, csv_source
from etl.load import load_bronze
from etl.run_context import RunContext
from etl.transform import build_layers
from pulse import sql as sql_assets
from pulse.config import DatabaseConfig, GeneratorConfig, StreamConfig
from pulse.db import Database, split_statements


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def test_generator_window_is_exactly_two_years():
    config = GeneratorConfig()
    assert (config.end_date - config.start_date).days == 729


def test_database_config_exposes_a_postgres_dsn():
    config = DatabaseConfig(engine="postgres", host="h", port=1234, database="d",
                            user="u", password="p")
    assert not config.is_duckdb
    assert "host=h" in config.dsn and "port=1234" in config.dsn


def test_postgres_dsn_carries_an_sslmode():
    """Azure Database for PostgreSQL sets require_secure_transport=ON and
    refuses a connection without TLS, so the DSN must always carry sslmode."""
    local = DatabaseConfig(engine="postgres", host="localhost")
    azure = DatabaseConfig(engine="postgres", host="x.postgres.database.azure.com",
                           sslmode="require")
    assert "sslmode=prefer" in local.dsn, "the local default must stay permissive"
    assert "sslmode=require" in azure.dsn


def test_stream_config_lists_all_four_topics():
    assert len(StreamConfig().topics) == 4


def test_unsupported_engine_is_rejected_immediately():
    with pytest.raises(ValueError):
        Database(DatabaseConfig(engine="oracle"))


# --------------------------------------------------------------------------- #
# SQL splitting and dialect handling
# --------------------------------------------------------------------------- #
def test_split_statements_splits_on_top_level_semicolons():
    assert split_statements("SELECT 1; SELECT 2;") == ["SELECT 1", "SELECT 2"]


def test_split_statements_ignores_semicolons_inside_strings():
    statements = split_statements("SELECT 'a;b' AS x; SELECT 2")
    assert len(statements) == 2
    assert "a;b" in statements[0]


def test_split_statements_strips_comment_lines():
    statements = split_statements("-- a comment\nSELECT 1;\n-- another\nSELECT 2;")
    assert statements == ["SELECT 1", "SELECT 2"]
    assert not any("comment" in s for s in statements)


def test_duckdb_dialect_translation():
    duck = Database(DatabaseConfig(engine="duckdb"))
    assert "DOUBLE" in duck._adapt("x DOUBLE PRECISION")
    assert "TIME ZONE" not in duck._adapt("t TIMESTAMP WITHOUT TIME ZONE")


def test_sql_assets_are_discovered_in_build_order():
    assert list(sql_assets.LAYERS) == ["init", "staging", "warehouse", "analytics"]
    for layer in sql_assets.LAYERS:
        files = sql_assets.layer_files(layer)
        assert files, f"no .sql files found for {layer}"
        assert files == sorted(files), f"{layer} files are not in filename order"


def test_every_sql_file_parses_into_statements():
    for path in sql_assets.all_files():
        statements = split_statements(path.read_text(encoding="utf-8"))
        assert statements, f"{path.name} produced no statements"


# --------------------------------------------------------------------------- #
# Extract
# --------------------------------------------------------------------------- #
def test_csv_extract_stamps_lineage(raw_dir):
    frame = csv_source.read_table("orders", raw_dir)
    assert "_loaded_at" in frame and "_source_file" in frame
    assert (frame["_source_file"] == "orders.csv").all()
    assert pd.api.types.is_datetime64_any_dtype(frame["order_ts"])


def test_csv_extract_names_the_fix_when_a_file_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError) as error:
        csv_source.read_table("orders", tmp_path)
    assert "generate_data.py" in str(error.value)


def test_all_source_tables_are_present(raw_dir):
    assert set(csv_source.available_tables(raw_dir)) == set(csv_source.SOURCE_TABLES)


def test_manifest_records_the_injected_defects(raw_dir):
    manifest = csv_source.manifest(raw_dir)
    assert manifest["row_counts"]["orders"] > 0
    assert manifest["injected_quality_issues"]["orders_duplicate_rows"] > 0


def test_fx_extractor_falls_back_without_a_network():
    """The pipeline must never fail because a public endpoint is down."""
    frame = api_source.fetch_fx_rates(days=5, allow_network=False)
    assert len(frame) == 5 * len(api_source.QUOTE_CURRENCIES)
    assert (frame["rate"] > 0).all()
    assert frame["source"].str.startswith("fallback").all(), \
        "a fallback rate must never be presented as a market rate"


def test_fx_extractor_is_deterministic_offline():
    first = api_source.fetch_fx_rates(days=3, allow_network=False,
                                      as_of=datetime(2025, 6, 1).date())
    second = api_source.fetch_fx_rates(days=3, allow_network=False,
                                       as_of=datetime(2025, 6, 1).date())
    pd.testing.assert_series_equal(first["rate"], second["rate"])


# --------------------------------------------------------------------------- #
# Load
# --------------------------------------------------------------------------- #
def test_bronze_load_aligns_to_the_declared_columns(db, raw_dir):
    frame = csv_source.read_table("regions", raw_dir)
    frame["an_unmapped_column"] = 1          # a source that grew a column
    aligned = load_bronze._align_to_table(frame, db, "regions")
    assert "an_unmapped_column" not in aligned.columns
    assert list(aligned.columns) == list(
        db.query("SELECT * FROM bronze.regions WHERE 1 = 0").columns
    )


def test_bronze_load_fails_loudly_when_a_column_disappears(db, raw_dir):
    frame = csv_source.read_table("regions", raw_dir).drop(columns=["region_name"])
    with pytest.raises(ValueError, match="missing source columns"):
        load_bronze._align_to_table(frame, db, "regions")


def test_fx_load_is_idempotent(db):
    first = load_bronze.load_fx_rates(db, days=5, allow_network=False)
    count_after_first = db.row_count("bronze", "fx_rates")
    second = load_bronze.load_fx_rates(db, days=5, allow_network=False)
    assert first == second
    assert db.row_count("bronze", "fx_rates") == count_after_first, \
        "re-running the pipeline on the same day doubled the FX rows"


def test_write_frame_round_trips(db):
    db.execute("DROP TABLE IF EXISTS ops.round_trip_test")
    db.execute("CREATE TABLE ops.round_trip_test (a INTEGER, b VARCHAR(20))")
    frame = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    assert db.write_frame(frame, "ops", "round_trip_test") == 3
    assert db.row_count("ops", "round_trip_test") == 3
    db.execute("DROP TABLE ops.round_trip_test")


def test_write_frame_truncates_by_default(db):
    db.execute("DROP TABLE IF EXISTS ops.truncate_test")
    db.execute("CREATE TABLE ops.truncate_test (a INTEGER)")
    frame = pd.DataFrame({"a": [1, 2]})
    db.write_frame(frame, "ops", "truncate_test", truncate=True)
    db.write_frame(frame, "ops", "truncate_test", truncate=True)
    assert db.row_count("ops", "truncate_test") == 2
    db.write_frame(frame, "ops", "truncate_test", truncate=False)
    assert db.row_count("ops", "truncate_test") == 4
    db.execute("DROP TABLE ops.truncate_test")


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def test_run_context_records_a_successful_stage(db):
    context = RunContext(pipeline="test", db=db)
    with context.stage("a stage that works") as stage:
        stage["rows_out"] = 42
    assert len(context.stages) == 1
    assert context.stages[0].status == "success"
    assert not context.failed

    stored = db.query(
        f"SELECT * FROM ops.pipeline_runs WHERE run_id = '{context.run_id}'"
    )
    assert len(stored) == 1
    assert int(stored.iloc[0]["rows_out"]) == 42


def test_run_context_records_a_failure_and_re_raises(db):
    context = RunContext(pipeline="test", db=db)
    with pytest.raises(RuntimeError, match="boom"):
        with context.stage("a stage that breaks"):
            raise RuntimeError("boom")
    assert context.failed
    assert context.stages[0].status == "failed"
    assert "boom" in context.stages[0].message


def test_layer_row_counts_report_what_was_built(db):
    counts = build_layers.layer_row_counts("warehouse", db)
    assert counts["gold.fact_orders"] > 0
    assert counts["gold.dim_customer"] > 0


def test_layer_contract_matches_what_the_sql_actually_creates(db):
    """The declared contract in LAYER_TABLES must not drift from reality."""
    for layer, tables in build_layers.LAYER_TABLES.items():
        for schema, table in tables:
            assert db.table_exists(schema, table), \
                f"{layer} claims to build {schema}.{table}, but it does not exist"


def test_pipeline_is_idempotent(db, raw_dir):
    """Running the whole thing twice must produce identical row counts."""
    before = build_layers.layer_row_counts("analytics", db)
    load_bronze.load_all(db, raw_dir=raw_dir, allow_network=False)
    build_layers.build_silver(db)
    build_layers.build_warehouse(db)
    after = build_layers.build_marts(db)
    assert before == after


def test_healthcheck_reports_the_engine(db):
    info = db.healthcheck()
    assert info["ok"] is True
    assert info["engine"] == "duckdb"


def test_ops_tables_survive_a_full_refresh(db, raw_dir):
    """A batch rebuild must not delete the run log or the streaming landing
    zone. A batch job that silently destroys the real-time layer is the kind of
    coupling that causes a 3am page.

    Re-running the init layer DOES drop and recreate bronze - that is the
    intended behaviour - so bronze is reloaded afterwards to leave the shared
    session warehouse as this test found it.
    """
    db.execute("DELETE FROM ops.stream_events")
    db.write_frame(
        pd.DataFrame([{
            "event_id": "survives-refresh", "topic": "pulse.orders",
            "event_type": "order_placed", "event_ts": datetime.now(),
            "ingested_at": datetime.now(), "customer_id": 1, "order_id": 1,
            "product_id": None, "store_id": 1, "region_id": 1, "channel": "Web",
            "status": "placed", "amount": 10.0, "quantity": 1, "payload": "{}",
        }]),
        "ops", "stream_events", truncate=False,
    )
    runs_before = db.row_count("ops", "pipeline_runs")

    try:
        build_layers.initialise_schemas(db)

        assert db.scalar(
            "SELECT COUNT(*) FROM ops.stream_events WHERE event_id = 'survives-refresh'"
        ) == 1, "a full refresh deleted the streaming landing zone"
        assert db.row_count("ops", "pipeline_runs") >= runs_before, \
            "a full refresh deleted the pipeline run history"
        assert db.row_count("bronze", "orders") == 0, \
            "the init layer is supposed to rebuild bronze from scratch"
    finally:
        load_bronze.load_all(db, raw_dir=raw_dir, allow_network=False)
