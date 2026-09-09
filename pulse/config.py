"""Central configuration.

Values come from environment variables (optionally loaded from a .env file at
the repository root). Every setting has a working default so the platform runs
with zero configuration on a laptop.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class DatabaseConfig:
    """Which SQL engine the platform talks to.

    ``duckdb``   - zero-install embedded engine, the local demo default.
    ``postgres`` - the production-shaped target started by docker-compose.
    """

    engine: str = field(default_factory=lambda: _env("PULSE_DB_ENGINE", "duckdb").lower())
    duckdb_path: Path = field(
        default_factory=lambda: Path(_env("PULSE_DUCKDB_PATH", str(ROOT / "data" / "warehouse" / "pulse.duckdb")))
    )
    host: str = field(default_factory=lambda: _env("POSTGRES_HOST", "localhost"))
    port: int = field(default_factory=lambda: _env_int("POSTGRES_PORT", 5432))
    database: str = field(default_factory=lambda: _env("POSTGRES_DB", "pulse"))
    user: str = field(default_factory=lambda: _env("POSTGRES_USER", "pulse"))
    password: str = field(default_factory=lambda: _env("POSTGRES_PASSWORD", "pulse"))
    # Azure Database for PostgreSQL sets require_secure_transport=ON, so a
    # connection without TLS is refused outright. `prefer` locally (the
    # docker-compose server has no certificate), `require` in the cloud - set by
    # Terraform on the container apps and by the deploy workflow's migration
    # step. The default stays permissive so the local demo needs no config.
    sslmode: str = field(default_factory=lambda: _env("POSTGRES_SSLMODE", "prefer"))

    @property
    def is_duckdb(self) -> bool:
        return self.engine == "duckdb"

    @property
    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={self.password} sslmode={self.sslmode}"
        )


@dataclass(frozen=True)
class StreamConfig:
    """Event bus settings.

    ``local`` writes newline-delimited JSON to ``data/stream`` and needs nothing
    running. ``kafka`` talks to Redpanda/Kafka on ``PULSE_KAFKA_BROKERS``.
    """

    backend: str = field(default_factory=lambda: _env("PULSE_STREAM_BACKEND", "local").lower())
    brokers: str = field(default_factory=lambda: _env("PULSE_KAFKA_BROKERS", "localhost:19092"))
    directory: Path = field(default_factory=lambda: Path(_env("PULSE_STREAM_DIR", str(ROOT / "data" / "stream"))))
    consumer_group: str = field(default_factory=lambda: _env("PULSE_CONSUMER_GROUP", "pulse-analytics"))

    TOPIC_ORDERS: str = "pulse.orders"
    TOPIC_PAYMENTS: str = "pulse.payments"
    TOPIC_INVENTORY: str = "pulse.inventory"
    TOPIC_ACTIVITY: str = "pulse.customer_activity"

    @property
    def topics(self) -> list[str]:
        return [self.TOPIC_ORDERS, self.TOPIC_PAYMENTS, self.TOPIC_INVENTORY, self.TOPIC_ACTIVITY]


@dataclass(frozen=True)
class GeneratorConfig:
    """Size and shape of the synthetic two-year dataset."""

    seed: int = field(default_factory=lambda: _env_int("PULSE_SEED", 20240101))
    customers: int = field(default_factory=lambda: _env_int("PULSE_N_CUSTOMERS", 4000))
    products: int = field(default_factory=lambda: _env_int("PULSE_N_PRODUCTS", 320))
    orders: int = field(default_factory=lambda: _env_int("PULSE_N_ORDERS", 60000))
    events: int = field(default_factory=lambda: _env_int("PULSE_N_EVENTS", 150000))
    campaigns: int = field(default_factory=lambda: _env_int("PULSE_N_CAMPAIGNS", 48))
    end_date: date = field(default_factory=lambda: date.fromisoformat(_env("PULSE_END_DATE", "2025-12-31")))

    @property
    def start_date(self) -> date:
        return self.end_date - timedelta(days=729)  # exactly two years of history


@dataclass(frozen=True)
class Paths:
    """Where data lives.

    Every location is overridable by environment variable, because on Azure
    these become ADLS mount points rather than folders in the repository -
    and that has to be a configuration change, not a code change.
    """

    root: Path = ROOT
    raw: Path = field(
        default_factory=lambda: Path(_env("PULSE_RAW_DIR", str(ROOT / "data" / "raw")))
    )
    warehouse: Path = field(
        default_factory=lambda: Path(_env("PULSE_WAREHOUSE_DIR", str(ROOT / "data" / "warehouse")))
    )
    stream: Path = field(
        default_factory=lambda: Path(_env("PULSE_STREAM_DIR", str(ROOT / "data" / "stream")))
    )
    exports: Path = field(
        default_factory=lambda: Path(_env("PULSE_EXPORT_DIR", str(ROOT / "data" / "exports")))
    )
    sql: Path = ROOT / "database"

    def ensure(self) -> "Paths":
        for directory in (self.raw, self.warehouse, self.stream, self.exports):
            directory.mkdir(parents=True, exist_ok=True)
        return self


DB = DatabaseConfig()
STREAM = StreamConfig()
GENERATOR = GeneratorConfig()
PATHS = Paths().ensure()

# Business constants used across analytics modules. Documented in
# docs/kpi-definitions.md so dashboards and SQL agree on one definition.
CHURN_WINDOW_DAYS = _env_int("PULSE_CHURN_WINDOW_DAYS", 90)
CURRENCY = _env("PULSE_CURRENCY", "USD")
