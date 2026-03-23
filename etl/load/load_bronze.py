"""Load: land extracted frames into the bronze schema.

Bronze is a truncate-and-reload of the batch extract plus an append-only FX
feed. Both modes are here because both are real: dimension-style extracts are
cheapest to replace wholesale, while an API feed is naturally incremental and
must not lose yesterday's rates.
"""
from __future__ import annotations

import pandas as pd

from pulse.db import Database, get_database
from pulse.logging_utils import get_logger
from etl.extract import api_source, csv_source

log = get_logger("etl.load.bronze")


def _align_to_table(frame: pd.DataFrame, db: Database, table: str) -> pd.DataFrame:
    """Keep only the columns the bronze table actually declares, in its order.

    A source that grows a new column should not break the load - it should be
    ignored until someone deliberately adds it to the model. A source that
    *drops* a column should break loudly, so a missing column raises.
    """
    target_columns = list(
        db.query(f"SELECT * FROM bronze.{table} WHERE 1 = 0").columns
    )
    missing = [c for c in target_columns if c not in frame.columns]
    if missing:
        raise ValueError(f"bronze.{table} is missing source columns: {missing}")
    extra = [c for c in frame.columns if c not in target_columns]
    if extra:
        log.warning("bronze.%s: ignoring %d unmapped source column(s): %s",
                    table, len(extra), ", ".join(extra))
    return frame[target_columns]


def load_batch_sources(db: Database | None = None, raw_dir=None) -> dict[str, int]:
    """Truncate-and-reload every CSV extract into bronze."""
    db = db or get_database()
    counts: dict[str, int] = {}
    for table in csv_source.available_tables(raw_dir):
        frame = csv_source.read_table(table, raw_dir)
        frame = _align_to_table(frame, db, table)
        counts[table] = db.write_frame(frame, "bronze", table, truncate=True)
    return counts


def load_fx_rates(db: Database | None = None, days: int = 30,
                  allow_network: bool = True) -> int:
    """Append the FX feed, replacing any rows we already hold for those dates."""
    db = db or get_database()
    frame = api_source.fetch_fx_rates(days=days, allow_network=allow_network)
    frame = _align_to_table(frame, db, "fx_rates")

    # Idempotent by design: rerunning the pipeline twice on the same day must
    # not double the rows.
    earliest = pd.to_datetime(frame["rate_date"]).min().date()
    db.execute(f"DELETE FROM bronze.fx_rates WHERE rate_date >= DATE '{earliest.isoformat()}'")
    return db.write_frame(frame, "bronze", "fx_rates", truncate=False)


def load_all(db: Database | None = None, raw_dir=None,
             allow_network: bool = True) -> dict[str, int]:
    db = db or get_database()
    counts = load_batch_sources(db, raw_dir)
    counts["fx_rates"] = load_fx_rates(db, allow_network=allow_network)
    total = sum(counts.values())
    log.info("bronze loaded: %s rows across %d tables", format(total, ","), len(counts))
    return counts
