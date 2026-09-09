"""Event contracts.

Every message on the bus has the same envelope, whatever topic it is on:

    event_id, event_type, event_ts, produced_at, source, version, payload

An envelope shared by all topics is what lets one consumer land every stream in
one table (``ops.stream_events``) and one dashboard query read all of them.
``version`` is there from day one because the day you need it is the day you
cannot add it.

The payload fields per topic are declared below rather than left implicit, so a
schema registry (or a Pydantic/Avro model in production) has something concrete
to be generated from.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

SCHEMA_VERSION = "1.0"

TOPIC_ORDERS = "pulse.orders"
TOPIC_PAYMENTS = "pulse.payments"
TOPIC_INVENTORY = "pulse.inventory"
TOPIC_ACTIVITY = "pulse.customer_activity"

ALL_TOPICS = [TOPIC_ORDERS, TOPIC_PAYMENTS, TOPIC_INVENTORY, TOPIC_ACTIVITY]

# Declared payload fields per topic. The consumer projects these into the
# columns of ops.stream_events; anything else stays in the raw payload blob.
PAYLOAD_FIELDS: dict[str, list[str]] = {
    TOPIC_ORDERS: [
        "order_id", "customer_id", "store_id", "region_id", "channel",
        "status", "amount", "quantity",
    ],
    TOPIC_PAYMENTS: [
        "payment_id", "order_id", "customer_id", "payment_method",
        "status", "amount", "failure_reason", "attempt_number",
    ],
    TOPIC_INVENTORY: [
        "product_id", "store_id", "status", "quantity", "reorder_point",
    ],
    TOPIC_ACTIVITY: [
        "customer_id", "session_id", "device", "product_id", "status",
    ],
}

# Columns of ops.stream_events that the consumer projects into.
PROJECTED_COLUMNS = [
    "event_id", "topic", "event_type", "event_ts", "ingested_at",
    "customer_id", "order_id", "product_id", "store_id", "region_id",
    "channel", "status", "amount", "quantity", "payload",
]


def make_event(topic: str, event_type: str, payload: dict[str, Any],
               event_ts: datetime | None = None) -> dict[str, Any]:
    """Wrap a payload in the standard envelope."""
    now = datetime.now()
    return {
        "event_id": uuid.uuid4().hex,
        "topic": topic,
        "event_type": event_type,
        "event_ts": (event_ts or now).isoformat(timespec="milliseconds"),
        "produced_at": now.isoformat(timespec="milliseconds"),
        "source": "pulse.simulator",
        "version": SCHEMA_VERSION,
        "payload": payload,
    }


def serialise(event: dict[str, Any]) -> bytes:
    return json.dumps(event, separators=(",", ":"), default=str).encode("utf-8")


def deserialise(raw: bytes | str) -> dict[str, Any]:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)


def _as_number(value: Any) -> Any:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def project(event: dict[str, Any]) -> dict[str, Any]:
    """Flatten an envelope into the ops.stream_events column layout.

    Unknown fields are not dropped - they stay in ``payload`` so a schema change
    upstream degrades into "we kept the data but did not model it yet" rather
    than data loss.
    """
    payload = event.get("payload") or {}
    numeric = {
        key: _as_number(payload.get(key))
        for key in ("customer_id", "order_id", "product_id", "store_id",
                    "region_id", "amount", "quantity")
    }
    return {
        "event_id": event.get("event_id"),
        "topic": event.get("topic"),
        "event_type": event.get("event_type"),
        "event_ts": event.get("event_ts"),
        "ingested_at": datetime.now(),
        "customer_id": None if numeric["customer_id"] is None else int(numeric["customer_id"]),
        "order_id": None if numeric["order_id"] is None else int(numeric["order_id"]),
        "product_id": None if numeric["product_id"] is None else int(numeric["product_id"]),
        "store_id": None if numeric["store_id"] is None else int(numeric["store_id"]),
        "region_id": None if numeric["region_id"] is None else int(numeric["region_id"]),
        "channel": payload.get("channel"),
        "status": payload.get("status"),
        "amount": numeric["amount"],
        "quantity": None if numeric["quantity"] is None else int(numeric["quantity"]),
        "payload": json.dumps(payload, separators=(",", ":"), default=str)[:4000],
    }
