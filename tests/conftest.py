"""Shared test fixtures.

The whole suite runs against a **real warehouse** built from a real generated
dataset, in a temporary DuckDB file - not against mocks. That is a deliberate
trade: the tests take about a minute instead of a second, and in exchange they
actually exercise the SQL, which is where the platform's logic lives. A mocked
test of a data pipeline verifies the mock.

The environment is configured before ``pulse.config`` is imported anywhere,
because that module reads its settings once at import time.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# --- must happen before any `pulse` import -------------------------------- #
_TEST_ROOT = Path(os.environ.get("PYTEST_TMP_ROOT", ROOT / ".pytest_warehouse"))
_TEST_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PULSE_DB_ENGINE", "duckdb")
os.environ.setdefault("PULSE_DUCKDB_PATH", str(_TEST_ROOT / "pulse_test.duckdb"))
os.environ.setdefault("PULSE_STREAM_DIR", str(_TEST_ROOT / "stream"))
os.environ.setdefault("PULSE_LOG_LEVEL", "WARNING")
# --------------------------------------------------------------------------- #

# A dataset small enough to build in seconds but large enough that cohort
# analysis, backtesting and RFM quintiles all have something to work with.
TEST_DATASET = dict(customers=150, products=30, orders=900, events=2000, campaigns=6)


def _load_generator():
    """Import the generator by path - its directory name is not a Python
    identifier, so it cannot be imported normally."""
    path = ROOT / "data-generator" / "generate_data.py"
    spec = importlib.util.spec_from_file_location("pulse_generator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def generator_module():
    return _load_generator()


@pytest.fixture(scope="session")
def raw_dir(tmp_path_factory, generator_module) -> Path:
    """Generate one small dataset for the whole session."""
    directory = tmp_path_factory.mktemp("raw")
    generator_module.main([
        "--seed", "424242",
        "--customers", str(TEST_DATASET["customers"]),
        "--products", str(TEST_DATASET["products"]),
        "--orders", str(TEST_DATASET["orders"]),
        "--events", str(TEST_DATASET["events"]),
        "--campaigns", str(TEST_DATASET["campaigns"]),
        "--output", str(directory),
    ])
    return directory


@pytest.fixture(scope="session")
def warehouse(raw_dir):
    """A fully built warehouse: bronze, silver, star schema and gold marts."""
    from etl.load import load_bronze
    from etl.transform import build_layers
    from pulse.db import get_database

    db = get_database()
    build_layers.initialise_schemas(db)
    # offline=True: the test suite must never depend on a network call.
    load_bronze.load_all(db, raw_dir=raw_dir, allow_network=False)
    build_layers.build_silver(db)
    build_layers.build_warehouse(db)
    build_layers.build_marts(db)
    return db


@pytest.fixture
def db(warehouse):
    return warehouse


@pytest.fixture
def stream_dir(tmp_path) -> Path:
    directory = tmp_path / "stream"
    directory.mkdir(parents=True, exist_ok=True)
    return directory
