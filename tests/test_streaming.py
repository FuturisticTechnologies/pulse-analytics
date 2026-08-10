"""The real-time layer.

The properties that matter for a streaming pipeline are not "does it emit JSON"
but: are the streams mutually consistent, does the consumer resume where it
stopped, and does a crash lose data or replay it. Those are what is tested here.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import pandas as pd
import pytest

from pulse.config import StreamConfig
from streaming import events
from streaming.bus import FileEventBus
from streaming.consumer.stream_consumer import StreamConsumer
from streaming.processors.kpi_processor import RealtimeKpiProcessor
from streaming.producer.event_producer import Catalogue, EventProducer


@pytest.fixture
def bus(stream_dir) -> FileEventBus:
    return FileEventBus(StreamConfig(backend="local", directory=stream_dir,
                                     consumer_group="test-group"))


def force_payments_due(producer: EventProducer) -> None:
    """Make every in-flight authorisation due immediately.

    The producer deliberately delays payments a few seconds behind their order,
    the way a real gateway integration does. A test must not sleep for that.
    """
    from collections import deque

    producer.state.pending_payments = deque(
        (0.0, *pending[1:]) for pending in producer.state.pending_payments
    )
    producer.emit_due_payments()


@pytest.fixture
def catalogue() -> Catalogue:
    return Catalogue(
        customers=list(range(1, 41)),
        products=[(i, 10.0 * i, 4) for i in range(1, 13)],
        stores=[(1, 1), (2, 2)],
        max_order_id=5000,
    )


# --------------------------------------------------------------------------- #
# Envelope
# --------------------------------------------------------------------------- #
def test_every_event_carries_the_standard_envelope():
    event = events.make_event(events.TOPIC_ORDERS, "order_placed",
                              {"order_id": 1, "amount": 25.0})
    for field in ("event_id", "topic", "event_type", "event_ts",
                  "produced_at", "source", "version", "payload"):
        assert field in event, f"envelope is missing {field}"
    assert event["version"] == events.SCHEMA_VERSION


def test_serialise_round_trips():
    event = events.make_event(events.TOPIC_PAYMENTS, "payment_failed",
                              {"order_id": 7, "amount": 12.5, "status": "failed"})
    assert events.deserialise(events.serialise(event)) == event


def test_projection_flattens_into_the_table_columns():
    event = events.make_event(events.TOPIC_ORDERS, "order_placed", {
        "order_id": 12, "customer_id": 3, "store_id": 2, "region_id": 1,
        "channel": "Web", "status": "placed", "amount": 99.5, "quantity": 2,
    })
    projected = events.project(event)
    assert set(projected) == set(events.PROJECTED_COLUMNS)
    assert projected["order_id"] == 12
    assert projected["amount"] == 99.5
    assert projected["quantity"] == 2


def test_projection_keeps_unmodelled_fields_in_the_payload():
    """A schema change upstream must degrade into 'kept but not modelled',
    never into data loss."""
    event = events.make_event(events.TOPIC_ORDERS, "order_placed",
                              {"order_id": 1, "brand_new_field": "surprise"})
    projected = events.project(event)
    assert "brand_new_field" in json.loads(projected["payload"])


def test_projection_survives_a_missing_or_unparseable_field():
    event = events.make_event(events.TOPIC_ORDERS, "order_placed",
                              {"order_id": "not-a-number"})
    projected = events.project(event)
    assert projected["order_id"] is None
    assert projected["customer_id"] is None


# --------------------------------------------------------------------------- #
# Bus
# --------------------------------------------------------------------------- #
def test_publish_then_consume_returns_the_same_events(bus):
    for index in range(5):
        bus.publish(events.TOPIC_ORDERS, str(index),
                    events.make_event(events.TOPIC_ORDERS, "order_placed",
                                      {"order_id": index}))
    bus.flush()
    consumed = list(bus.consume([events.TOPIC_ORDERS]))
    assert len(consumed) == 5
    assert [e["payload"]["order_id"] for e in consumed] == list(range(5))


def test_offsets_are_committed_so_a_restart_does_not_replay(bus):
    for index in range(3):
        bus.publish(events.TOPIC_ORDERS, "k",
                    events.make_event(events.TOPIC_ORDERS, "order_placed",
                                      {"order_id": index}))
    bus.flush()
    assert len(list(bus.consume([events.TOPIC_ORDERS]))) == 3
    assert len(list(bus.consume([events.TOPIC_ORDERS]))) == 0, \
        "the second poll replayed events that were already committed"

    bus.publish(events.TOPIC_ORDERS, "k",
                events.make_event(events.TOPIC_ORDERS, "order_placed",
                                  {"order_id": 99}))
    bus.flush()
    tail = list(bus.consume([events.TOPIC_ORDERS]))
    assert len(tail) == 1 and tail[0]["payload"]["order_id"] == 99


def test_reset_replays_the_whole_log(bus):
    for index in range(4):
        bus.publish(events.TOPIC_ORDERS, "k",
                    events.make_event(events.TOPIC_ORDERS, "o", {"order_id": index}))
    bus.flush()
    list(bus.consume([events.TOPIC_ORDERS]))
    bus.reset([events.TOPIC_ORDERS])
    assert len(list(bus.consume([events.TOPIC_ORDERS]))) == 4


def test_max_messages_bounds_the_batch(bus):
    for index in range(50):
        bus.publish(events.TOPIC_ORDERS, "k",
                    events.make_event(events.TOPIC_ORDERS, "o", {"order_id": index}))
    bus.flush()
    assert len(list(bus.consume([events.TOPIC_ORDERS], max_messages=10))) == 10


def test_a_malformed_line_is_skipped_not_fatal(bus, stream_dir):
    bus.publish(events.TOPIC_ORDERS, "k",
                events.make_event(events.TOPIC_ORDERS, "o", {"order_id": 1}))
    bus.flush()
    with open(stream_dir / f"{events.TOPIC_ORDERS}.jsonl", "a", encoding="utf-8") as f:
        f.write("{ this is not json }\n")
    bus.publish(events.TOPIC_ORDERS, "k",
                events.make_event(events.TOPIC_ORDERS, "o", {"order_id": 2}))
    bus.flush()

    consumed = list(bus.consume([events.TOPIC_ORDERS]))
    assert [e["payload"]["order_id"] for e in consumed] == [1, 2]


def test_backlog_reports_unread_bytes(bus):
    assert bus.backlog([events.TOPIC_ORDERS])[events.TOPIC_ORDERS] == 0
    bus.publish(events.TOPIC_ORDERS, "k",
                events.make_event(events.TOPIC_ORDERS, "o", {"order_id": 1}))
    bus.flush()
    assert bus.backlog([events.TOPIC_ORDERS])[events.TOPIC_ORDERS] > 0
    list(bus.consume([events.TOPIC_ORDERS]))
    assert bus.backlog([events.TOPIC_ORDERS])[events.TOPIC_ORDERS] == 0


# --------------------------------------------------------------------------- #
# Producer
# --------------------------------------------------------------------------- #
def test_producer_emits_correlated_streams(bus, catalogue):
    """Every payment must reference an order that was actually placed. A payment
    for a phantom order makes every downstream join a lie."""
    producer = EventProducer(bus, catalogue, seed=3)
    for _ in range(40):
        producer.emit_order()
    force_payments_due(producer)
    bus.flush()

    order_ids, payment_order_ids = set(), set()
    for event in bus.consume([events.TOPIC_ORDERS, events.TOPIC_PAYMENTS],
                             max_messages=5000):
        if event["topic"] == events.TOPIC_ORDERS:
            order_ids.add(event["payload"]["order_id"])
        else:
            payment_order_ids.add(event["payload"]["order_id"])

    assert order_ids
    assert payment_order_ids <= order_ids, "a payment referenced a phantom order"


def test_producer_only_references_real_customers_and_products(bus, catalogue):
    producer = EventProducer(bus, catalogue, seed=4)
    for _ in range(30):
        producer.emit_order()
        producer.emit_activity()
    bus.flush()

    valid_customers = set(catalogue.customers)
    valid_products = {p[0] for p in catalogue.products}
    for event in bus.consume(events.ALL_TOPICS, max_messages=5000):
        payload = event["payload"]
        if payload.get("customer_id") is not None:
            assert payload["customer_id"] in valid_customers
        if payload.get("product_id") is not None:
            assert payload["product_id"] in valid_products


def test_producer_fires_inventory_alerts_when_stock_crosses_the_reorder_point(
        bus, catalogue):
    producer = EventProducer(bus, catalogue, seed=5)
    for _ in range(150):
        producer.emit_order()
    bus.flush()
    alerts = [e for e in bus.consume([events.TOPIC_INVENTORY], max_messages=5000)]
    assert alerts, "150 orders drained no product below its reorder point"
    assert {e["payload"]["status"] for e in alerts} <= {"low_stock", "stockout"}


def test_failed_payments_are_retried_at_most_once(bus, catalogue):
    producer = EventProducer(bus, catalogue, seed=6, failure_rate=1.0)
    producer.emit_order()
    for _ in range(4):
        force_payments_due(producer)
    bus.flush()
    attempts = [e["payload"]["attempt_number"]
                for e in bus.consume([events.TOPIC_PAYMENTS], max_messages=100)]
    assert max(attempts) <= 2, "an order was retried more than once"


def test_backfill_writes_events_with_past_timestamps(bus, catalogue):
    from streaming.producer.event_producer import backfill_history

    emitted = backfill_history(bus, catalogue, minutes=6, orders_per_minute=2, seed=1)
    assert emitted > 0
    now = datetime.now()
    stamps = [pd.to_datetime(e["event_ts"])
              for e in bus.consume([events.TOPIC_ORDERS], max_messages=5000)]
    assert stamps
    assert min(stamps) < now - timedelta(minutes=1)


# --------------------------------------------------------------------------- #
# Consumer and KPI processor
# --------------------------------------------------------------------------- #
def test_consumer_lands_events_and_computes_kpis(db, bus, catalogue):
    db.execute("DELETE FROM ops.stream_events")
    db.execute("DELETE FROM ops.realtime_kpis")

    producer = EventProducer(bus, catalogue, seed=8)
    for _ in range(25):
        producer.emit_order()
        producer.emit_activity()
    force_payments_due(producer)
    bus.flush()

    consumer = StreamConsumer(bus=bus, db=db, batch_size=1000)
    written = consumer.drain_once(timeout=2.0)
    assert written > 0
    assert db.row_count("ops", "stream_events") == written

    snapshot = consumer.processor.compute_and_store()
    assert snapshot is not None
    assert snapshot["orders"] == 25
    assert snapshot["revenue"] > 0
    assert snapshot["avg_order_value"] == pytest.approx(
        snapshot["revenue"] / snapshot["orders"], rel=1e-3
    )
    assert 0 <= snapshot["failure_rate_pct"] <= 100
    assert db.row_count("ops", "realtime_kpis") == 1


def test_kpi_window_uses_event_time_not_wall_clock(db, bus, catalogue):
    """A replayed stream must reproduce the KPIs it produced live."""
    db.execute("DELETE FROM ops.stream_events")
    producer = EventProducer(bus, catalogue, seed=9)
    old = datetime.now() - timedelta(hours=6)
    for index in range(5):
        producer._publish(events.TOPIC_ORDERS, "order_placed",
                          {"order_id": 90000 + index, "customer_id": 1,
                           "amount": 100.0, "status": "placed"},
                          key="k", event_ts=old + timedelta(minutes=index))
    bus.flush()
    StreamConsumer(bus=bus, db=db).drain_once(timeout=2.0)

    # Six hours old, so a wall-clock window would report nothing at all.
    snapshot = RealtimeKpiProcessor(db, window_minutes=60).compute()
    assert snapshot is not None
    assert snapshot["orders"] == 5
    assert snapshot["revenue"] == pytest.approx(500.0)


def test_processor_returns_none_on_an_empty_stream(db):
    db.execute("DELETE FROM ops.stream_events")
    assert RealtimeKpiProcessor(db).compute() is None


def test_consumer_commits_only_after_a_successful_write(db, bus, catalogue):
    """At-least-once delivery: an uncommitted batch must be re-delivered."""
    db.execute("DELETE FROM ops.stream_events")
    producer = EventProducer(bus, catalogue, seed=10)
    for _ in range(5):
        producer.emit_order()
    bus.flush()

    before = bus.backlog([events.TOPIC_ORDERS])[events.TOPIC_ORDERS]
    assert before > 0
    StreamConsumer(bus=bus, db=db).drain_once(timeout=2.0)
    assert bus.backlog([events.TOPIC_ORDERS])[events.TOPIC_ORDERS] == 0


def test_realtime_views_read_the_landed_events(db, bus, catalogue):
    db.execute("DELETE FROM ops.stream_events")
    producer = EventProducer(bus, catalogue, seed=12)
    for _ in range(10):
        producer.emit_order()
    bus.flush()
    StreamConsumer(bus=bus, db=db).drain_once(timeout=2.0)

    minutes = db.query("SELECT * FROM gold.v_realtime_orders")
    assert not minutes.empty
    assert minutes["orders"].sum() == 10
