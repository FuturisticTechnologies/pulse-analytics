"""Extract: the batch source system.

In production this is a nightly dump from the OLTP database landing on ADLS.
Locally it is ``data/raw/*.csv``. The interface is identical either way, which
is the point: nothing downstream of here knows or cares where the bytes came
from.

Typing is done HERE, not in the database, because a CSV has no types and
letting the warehouse guess is how a customer_id becomes a float.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from pulse.config import PATHS
from pulse.logging_utils import get_logger

log = get_logger("etl.extract.csv")

# Column -> pandas dtype hints per table. Anything not listed is inferred.
DATE_COLUMNS: dict[str, list[str]] = {}

# Tables in dependency order. Bronze has no constraints, but loading in this
# order keeps the logs readable and matches the order a real CDC feed arrives.
SOURCE_TABLES: list[str] = [
    "regions",
    "stores",
    "products",
    "customers",
    "campaigns",
    "orders",
    "order_items",
    "payments",
    "inventory_snapshots",
    "customer_events",
]


def source_path(table: str, raw_dir: Path | None = None) -> Path:
    return (raw_dir or PATHS.raw) / f"{table}.csv"


def available_tables(raw_dir: Path | None = None) -> list[str]:
    return [t for t in SOURCE_TABLES if source_path(t, raw_dir).exists()]


def read_table(table: str, raw_dir: Path | None = None) -> pd.DataFrame:
    """Read one source extract and stamp it with load metadata."""
    path = source_path(table, raw_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found - run: python data-generator/generate_data.py --preset small"
        )

    frame = pd.read_csv(path)
    for column in DATE_COLUMNS.get(table, []):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")

    # Lineage columns. Every bronze row can be traced back to a file and a time,
    # which is the minimum an auditor will ask for.
    frame["_loaded_at"] = datetime.now()
    frame["_source_file"] = path.name

    log.info("extracted %-22s %9s rows", table, format(len(frame), ","))
    return frame


def read_all(raw_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    return {table: read_table(table, raw_dir) for table in available_tables(raw_dir)}


def manifest(raw_dir: Path | None = None) -> dict:
    """The generator's manifest - row counts and the injected-defect ledger."""
    import json

    path = (raw_dir or PATHS.raw) / "_manifest.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
