"""Simulated live source systems.

Emits four correlated streams that behave the way real ones do:

  pulse.orders             orders as they are placed
  pulse.payments           the authorisation attempt for each order, arriving a
                           few seconds later - sometimes failing, sometimes
                           retried and captured on the second attempt
  pulse.inventory          stock decrements, with low_stock and stockout alerts
                           fired when a product crosses its reorder point
  pulse.customer_activity  clickstream, at roughly 12x the order rate

The correlation is the point. Anyone can emit random JSON; a payment event that
references an order that was never placed makes every downstream join a lie, so
the producer holds real state: open orders awaiting payment, live stock levels
per product, and active sessions.

    python -m streaming.producer.event_producer --rate 8 --duration 60
    python -m streaming.producer.event_producer --rate 40 --duration 0   # forever
"""
from __future__ import annotations

import argparse
import random
import signal
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

from pulse.config import PATHS
from pulse.db import get_database
from pulse.logging_utils import banner, get_logger
from streaming import events
from streaming.bus import EventBus, get_bus

log = get_logger("streaming.producer")

ORDER_CHANNELS = ["Web", "Mobile App", "In-Store", "Marketplace", "Phone"]
CHANNEL_WEIGHTS = [0.44, 0.32, 0.13, 0.08, 0.03]
PAYMENT_METHODS = ["Credit Card", "Debit Card", "PayPal", "Apple Pay", "Bank Transfer"]
PAYMENT_WEIGHTS = [0.38, 0.20, 0.19, 0.16, 0.07]
FAILURE_REASONS = ["insufficient_funds", "card_expired", "do_not_honor",
                   "network_timeout", "fraud_suspected", "invalid_cvc"]
ACTIVITY_TYPES = ["app_open", "page_view", "product_view", "search",
                  "add_to_cart", "checkout_start"]
ACTIVITY_WEIGHTS = [0.14, 0.32, 0.24, 0.12, 0.11, 0.07]
DEVICES = ["ios", "android", "desktop", "tablet"]

PAYMENT_FAILURE_RATE = 0.07     # ~7% of first attempts decline
RETRY_SUCCESS_RATE = 0.55       # just over half of declines recover on retry


@dataclass
class Catalogue:
    """Reference data the producer needs to emit *valid* events.

    Loaded from the warehouse when it exists, otherwise synthesised. The
    producer must be runnable before the batch pipeline has ever been run -
    demanding a built warehouse to demo the stream would be a circular
    dependency in the demo itself.
    """

    customers: list[int]
    products: list[tuple[int, float, int]]      # (product_id, unit_price, reorder_point)
    stores: list[tuple[int, int]]               # (store_id, region_id)
    max_order_id: int

    @classmethod
    def load(cls) -> "Catalogue":
        try:
            db = get_database()
            if db.table_exists("silver", "customers"):
                customers = db.query(
                    "SELECT customer_id FROM silver.customers"
                )["customer_id"].astype(int).tolist()
                products = list(db.query(
                    "SELECT product_id, unit_price FROM silver.products"
                ).itertuples(index=False, name=None))
                stores = list(db.query(
                    "SELECT store_id, region_id FROM silver.stores"
                ).itertuples(index=False, name=None))
                max_order = int(db.scalar("SELECT COALESCE(MAX(order_id), 0) FROM silver.orders") or 0)
                log.info("catalogue from warehouse: %d customers, %d products",
                         len(customers), len(products))
                return cls(
                    customers=[int(c) for c in customers],
                    products=[(int(p), float(v), max(4, int(v // 20) + 5)) for p, v in products],
                    stores=[(int(s), int(r)) for s, r in stores],
                    max_order_id=max_order,
                )
        except Exception as exc:
            log.warning("could not read the warehouse (%s) - synthesising a catalogue", exc)

        rng = random.Random(20240101)
        return cls(
            customers=list(range(1, 401)),
            products=[(i, round(rng.uniform(9, 900), 2), rng.randint(5, 40)) for i in range(1, 61)],
            stores=[(i, (i % 6) + 1) for i in range(1, 15)],
            max_order_id=100000,
        )


@dataclass
class ProducerState:
    """Everything that makes the streams mutually consistent."""

    stock: dict[int, int] = field(default_factory=dict)
    pending_payments: deque = field(default_factory=deque)
    sessions: dict[int, str] = field(default_factory=dict)
    next_order_id: int = 1
    next_payment_id: int = 1
    counts: dict[str, int] = field(default_factory=lambda: {
        events.TOPIC_ORDERS: 0, events.TOPIC_PAYMENTS: 0,
        events.TOPIC_INVENTORY: 0, events.TOPIC_ACTIVITY: 0,
    })


class EventProducer:
    def __init__(self, bus: EventBus, catalogue: Catalogue, seed: int = 7,
                 failure_rate: float = PAYMENT_FAILURE_RATE) -> None:
        self.bus = bus
        self.catalogue = catalogue
        self.rng = random.Random(seed)
        self.failure_rate = failure_rate
        self.state = ProducerState(next_order_id=catalogue.max_order_id + 1,
                                   next_payment_id=catalogue.max_order_id + 1)
        self.state.stock = {
            pid: self.rng.randint(reorder + 2, reorder * 3)
            for pid, _price, reorder in catalogue.products
        }
        # Demand follows a power law: a handful of products carry most of the
        # volume. Uniform product choice would spread decrements so thinly that
        # nothing ever crosses a reorder point, and the inventory stream would
        # be permanently silent - a demo that quietly proves nothing.
        self._product_weights = [
            1.0 / (rank + 1) ** 0.9 for rank in range(len(catalogue.products))
        ]

    def _pick_product(self) -> tuple[int, float, int]:
        return self.rng.choices(self.catalogue.products, weights=self._product_weights, k=1)[0]

    # ------------------------------------------------------------------ emit
    def _publish(self, topic: str, event_type: str, payload: dict,
                 key: str, event_ts: datetime | None = None) -> None:
        self.bus.publish(topic, key, events.make_event(topic, event_type, payload, event_ts))
        self.state.counts[topic] += 1

    def emit_order(self) -> None:
        rng = self.rng
        order_id = self.state.next_order_id
        self.state.next_order_id += 1

        customer_id = rng.choice(self.catalogue.customers)
        store_id, region_id = rng.choice(self.catalogue.stores)
        channel = rng.choices(ORDER_CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0]

        basket = rng.randint(1, 4)
        amount = 0.0
        for _ in range(basket):
            product_id, unit_price, reorder_point = self._pick_product()
            quantity = rng.randint(1, 3)
            amount += unit_price * quantity
            self._decrement_stock(product_id, quantity, reorder_point, store_id)

        amount = round(amount * rng.uniform(0.88, 1.0), 2)   # promotions
        self._publish(
            events.TOPIC_ORDERS, "order_placed",
            {
                "order_id": order_id, "customer_id": customer_id, "store_id": store_id,
                "region_id": region_id, "channel": channel, "status": "placed",
                "amount": amount, "quantity": basket,
            },
            key=str(customer_id),
        )
        # The authorisation lands a few seconds later, exactly as it would in a
        # real gateway integration.
        self.state.pending_payments.append(
            (time.time() + rng.uniform(0.4, 3.0), order_id, customer_id, amount, 1)
        )

    def _decrement_stock(self, product_id: int, quantity: int,
                         reorder_point: int, store_id: int) -> None:
        before = self.state.stock.get(product_id, reorder_point * 4)
        after = max(before - quantity, 0)
        self.state.stock[product_id] = after

        status = "ok"
        if after == 0:
            status = "stockout"
        elif after <= reorder_point:
            status = "low_stock"

        # Only publish an inventory event when something interesting happened -
        # a stream of "stock is still fine" messages is noise that costs money
        # to move and store.
        if status != "ok" or before > reorder_point >= after:
            self._publish(
                events.TOPIC_INVENTORY, f"inventory_{status}",
                {
                    "product_id": product_id, "store_id": store_id, "status": status,
                    "quantity": after, "reorder_point": reorder_point,
                },
                key=str(product_id),
            )
            if status == "stockout":
                # Restock arrives on the next cycle, so the demo keeps trading.
                self.state.stock[product_id] = reorder_point * 5

    def emit_due_payments(self) -> None:
        now = time.time()
        while self.state.pending_payments and self.state.pending_payments[0][0] <= now:
            _due, order_id, customer_id, amount, attempt = self.state.pending_payments.popleft()
            payment_id = self.state.next_payment_id
            self.state.next_payment_id += 1

            method = self.rng.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHTS, k=1)[0]
            failed = self.rng.random() < (self.failure_rate if attempt == 1 else 1 - RETRY_SUCCESS_RATE)
            status = "failed" if failed else "captured"
            reason = self.rng.choice(FAILURE_REASONS) if failed else None

            self._publish(
                events.TOPIC_PAYMENTS,
                "payment_failed" if failed else "payment_captured",
                {
                    "payment_id": payment_id, "order_id": order_id,
                    "customer_id": customer_id, "payment_method": method,
                    "status": status, "amount": amount,
                    "failure_reason": reason, "attempt_number": attempt,
                },
                key=str(order_id),
            )
            if failed and attempt < 2:
                self.state.pending_payments.append(
                    (now + self.rng.uniform(2.0, 6.0), order_id, customer_id, amount, attempt + 1)
                )

    def emit_activity(self) -> None:
        rng = self.rng
        customer_id = rng.choice(self.catalogue.customers)
        session_id = self.state.sessions.get(customer_id)
        if session_id is None or rng.random() < 0.25:
            session_id = f"s-{rng.getrandbits(40):x}"
            self.state.sessions[customer_id] = session_id

        event_type = rng.choices(ACTIVITY_TYPES, weights=ACTIVITY_WEIGHTS, k=1)[0]
        product_id = self._pick_product()[0] if event_type in (
            "product_view", "add_to_cart") else None

        self._publish(
            events.TOPIC_ACTIVITY, event_type,
            {
                "customer_id": customer_id, "session_id": session_id,
                "device": rng.choice(DEVICES), "product_id": product_id,
                "status": event_type,
            },
            key=str(customer_id),
        )

    # ------------------------------------------------------------------- run
    def run(self, rate_per_sec: float, duration_sec: float,
            activity_multiplier: int = 12) -> dict[str, int]:
        """Emit at ``rate_per_sec`` orders/second. ``duration_sec=0`` runs until
        interrupted."""
        stop = {"flag": False}

        def _handle(_signum, _frame):
            log.info("stop requested - flushing")
            stop["flag"] = True

        signal.signal(signal.SIGINT, _handle)
        try:
            signal.signal(signal.SIGTERM, _handle)
        except (AttributeError, ValueError):  # pragma: no cover - Windows quirks
            pass

        interval = 1.0 / max(rate_per_sec, 0.01)
        started = time.time()
        last_report = started
        emitted_orders = 0

        while not stop["flag"]:
            self.emit_order()
            emitted_orders += 1
            for _ in range(activity_multiplier):
                self.emit_activity()
            self.emit_due_payments()

            if time.time() - last_report >= 5.0:
                self._report(started)
                last_report = time.time()
                self.bus.flush()

            if duration_sec and (time.time() - started) >= duration_sec:
                break
            time.sleep(interval)

        # Drain the payments still in flight so no order is left unpaid.
        deadline = time.time() + 8
        while self.state.pending_payments and time.time() < deadline:
            time.sleep(0.25)
            self.emit_due_payments()

        self.bus.flush()
        self._report(started, final=True)
        return dict(self.state.counts)

    def _report(self, started: float, final: bool = False) -> None:
        elapsed = max(time.time() - started, 0.001)
        total = sum(self.state.counts.values())
        log.info(
            "%s%s events in %.1fs (%.0f/s) | orders=%s payments=%s inventory=%s activity=%s",
            "FINAL " if final else "",
            format(total, ","), elapsed, total / elapsed,
            format(self.state.counts[events.TOPIC_ORDERS], ","),
            format(self.state.counts[events.TOPIC_PAYMENTS], ","),
            format(self.state.counts[events.TOPIC_INVENTORY], ","),
            format(self.state.counts[events.TOPIC_ACTIVITY], ","),
        )


def backfill_history(bus: EventBus, catalogue: Catalogue, minutes: int = 45,
                     orders_per_minute: int = 6, seed: int = 11) -> int:
    """Write a plausible recent history so the live dashboard is never empty.

    Without this, the first thing anyone sees when they open the real-time page
    is a blank chart - which reads as "broken", not as "no data yet".
    """
    producer = EventProducer(bus, catalogue, seed=seed)
    now = datetime.now()
    emitted = 0
    rng = random.Random(seed)

    for minute in range(minutes, 0, -1):
        stamp = now - timedelta(minutes=minute)
        # A gentle daily shape so the chart has texture rather than a flat line.
        count = max(1, int(orders_per_minute * rng.uniform(0.55, 1.5)))
        for _ in range(count):
            offset = timedelta(seconds=rng.uniform(0, 59))
            order_id = producer.state.next_order_id
            producer.state.next_order_id += 1
            customer_id = rng.choice(catalogue.customers)
            store_id, region_id = rng.choice(catalogue.stores)
            amount = round(rng.uniform(35, 850), 2)

            producer._publish(
                events.TOPIC_ORDERS, "order_placed",
                {"order_id": order_id, "customer_id": customer_id, "store_id": store_id,
                 "region_id": region_id,
                 "channel": rng.choices(ORDER_CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0],
                 "status": "placed", "amount": amount, "quantity": rng.randint(1, 4)},
                key=str(customer_id), event_ts=stamp + offset,
            )
            failed = rng.random() < PAYMENT_FAILURE_RATE
            producer._publish(
                events.TOPIC_PAYMENTS,
                "payment_failed" if failed else "payment_captured",
                {"payment_id": order_id, "order_id": order_id, "customer_id": customer_id,
                 "payment_method": rng.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHTS, k=1)[0],
                 "status": "failed" if failed else "captured", "amount": amount,
                 "failure_reason": rng.choice(FAILURE_REASONS) if failed else None,
                 "attempt_number": 1},
                key=str(order_id), event_ts=stamp + offset + timedelta(seconds=3),
            )
            emitted += 2

            for _ in range(rng.randint(6, 14)):
                producer._publish(
                    events.TOPIC_ACTIVITY,
                    rng.choices(ACTIVITY_TYPES, weights=ACTIVITY_WEIGHTS, k=1)[0],
                    {"customer_id": rng.choice(catalogue.customers),
                     "session_id": f"s-{rng.getrandbits(40):x}",
                     "device": rng.choice(DEVICES), "product_id": None,
                     "status": "browse"},
                    key="backfill", event_ts=stamp + offset,
                )
                emitted += 1

    bus.flush()
    log.info("backfilled %s historical events over %d minutes", format(emitted, ","), minutes)
    return emitted


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Produce PulseAnalytics live events")
    parser.add_argument("--rate", type=float, default=6.0, help="orders per second")
    parser.add_argument("--duration", type=float, default=30.0,
                        help="seconds to run; 0 = until interrupted")
    parser.add_argument("--activity-multiplier", type=int, default=12,
                        help="clickstream events emitted per order")
    parser.add_argument("--failure-rate", type=float, default=PAYMENT_FAILURE_RATE,
                        help="first-attempt payment decline rate")
    parser.add_argument("--backfill-minutes", type=int, default=0,
                        help="write this many minutes of history first, then exit")
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    PATHS.ensure()
    print(banner("PulseAnalytics - event producer"))

    catalogue = Catalogue.load()
    with get_bus() as bus:
        if args.backfill_minutes:
            backfill_history(bus, catalogue, minutes=args.backfill_minutes)
            return 0
        producer = EventProducer(bus, catalogue, seed=args.seed,
                                 failure_rate=args.failure_rate)
        counts = producer.run(args.rate, args.duration, args.activity_multiplier)

    print("\n" + pd.Series(counts).to_string() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
