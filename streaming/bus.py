"""The event bus abstraction and its two implementations.

Interface, deliberately tiny:

    bus.publish(topic, key, event)      -> None
    bus.flush()                         -> None
    bus.consume(topics, max_messages, timeout) -> Iterator[dict]

Committed offsets are the only genuinely subtle part. The file bus keeps a
per-(group, topic) byte offset in ``data/stream/_offsets``; Kafka keeps them in
the broker. Both mean the same thing: restart the consumer and it resumes where
it stopped rather than replaying the day.
"""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterator

from pulse.config import STREAM, StreamConfig
from pulse.logging_utils import get_logger
from streaming.events import deserialise, serialise

log = get_logger("streaming.bus")


class EventBus(ABC):
    @abstractmethod
    def publish(self, topic: str, key: str, event: dict[str, Any]) -> None: ...

    @abstractmethod
    def consume(self, topics: list[str], max_messages: int = 500,
                timeout: float = 1.0) -> Iterator[dict[str, Any]]: ...

    def flush(self) -> None:
        """Block until buffered messages are handed to the broker."""

    def close(self) -> None:
        self.flush()

    def __enter__(self) -> "EventBus":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()


# --------------------------------------------------------------------------- #
# Local file bus - the zero-dependency default
# --------------------------------------------------------------------------- #
class FileEventBus(EventBus):
    """Append-only NDJSON per topic, with committed byte offsets per group.

    Not a broker: no partitions, no replication, no back-pressure. It is a
    faithful enough model of "an ordered, durable, replayable log" that the
    producer and consumer written against it work unchanged on Kafka.
    """

    def __init__(self, config: StreamConfig | None = None) -> None:
        self.config = config or STREAM
        self.directory = Path(self.config.directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.offset_dir = self.directory / "_offsets"
        self.offset_dir.mkdir(parents=True, exist_ok=True)
        self._handles: dict[str, Any] = {}

    # ------------------------------------------------------------- produce
    def _topic_path(self, topic: str) -> Path:
        return self.directory / f"{topic}.jsonl"

    def publish(self, topic: str, key: str, event: dict[str, Any]) -> None:
        handle = self._handles.get(topic)
        if handle is None:
            handle = open(self._topic_path(topic), "a", encoding="utf-8")
            self._handles[topic] = handle
        handle.write(serialise(event).decode("utf-8") + "\n")

    def flush(self) -> None:
        for handle in self._handles.values():
            handle.flush()

    def close(self) -> None:
        self.flush()
        for handle in self._handles.values():
            handle.close()
        self._handles.clear()

    # ------------------------------------------------------------- consume
    def _offset_path(self, topic: str) -> Path:
        return self.offset_dir / f"{self.config.consumer_group}.{topic}.offset"

    def committed_offset(self, topic: str) -> int:
        path = self._offset_path(topic)
        if not path.exists():
            return 0
        try:
            return int(path.read_text(encoding="utf-8").strip() or 0)
        except ValueError:
            return 0

    def commit(self, topic: str, offset: int) -> None:
        self._offset_path(topic).write_text(str(offset), encoding="utf-8")

    def reset(self, topics: list[str] | None = None) -> None:
        """Rewind to the start of the log - used by the replay demo."""
        for topic in topics or self.config.topics:
            path = self._offset_path(topic)
            if path.exists():
                path.unlink()

    def consume(self, topics: list[str], max_messages: int = 500,
                timeout: float = 1.0) -> Iterator[dict[str, Any]]:
        deadline = time.time() + timeout
        delivered = 0
        for topic in topics:
            path = self._topic_path(topic)
            if not path.exists():
                continue
            offset = self.committed_offset(topic)
            with open(path, "r", encoding="utf-8") as handle:
                handle.seek(offset)
                # readline() rather than `for line in handle`: iterating a text
                # file disables tell(), and the committed offset is the whole
                # point of this class.
                while True:
                    raw = handle.readline()
                    if not raw:
                        break
                    if not raw.endswith("\n"):
                        # Partial line - the producer is mid-write. Leave the
                        # offset before it and pick it up on the next poll.
                        break
                    line = raw.strip()
                    if not line:
                        offset = handle.tell()
                        continue
                    try:
                        event = deserialise(line)
                    except json.JSONDecodeError:
                        log.warning("skipping malformed event in %s at offset %d",
                                    topic, offset)
                        offset = handle.tell()
                        continue
                    yield event
                    delivered += 1
                    offset = handle.tell()
                    if delivered >= max_messages or time.time() > deadline:
                        break
            self.commit(topic, offset)
            if delivered >= max_messages:
                return

    def backlog(self, topics: list[str] | None = None) -> dict[str, int]:
        """Unread bytes per topic - the file bus's version of consumer lag."""
        result: dict[str, int] = {}
        for topic in topics or self.config.topics:
            path = self._topic_path(topic)
            size = path.stat().st_size if path.exists() else 0
            result[topic] = max(size - self.committed_offset(topic), 0)
        return result


# --------------------------------------------------------------------------- #
# Kafka / Redpanda / Event Hubs
# --------------------------------------------------------------------------- #
class KafkaEventBus(EventBus):
    """confluent-kafka implementation. Imported lazily so the local demo has
    no dependency on it at all."""

    def __init__(self, config: StreamConfig | None = None) -> None:
        self.config = config or STREAM
        try:
            from confluent_kafka import Consumer, Producer
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "PULSE_STREAM_BACKEND=kafka needs confluent-kafka: "
                "pip install -r requirements-optional.txt"
            ) from exc

        self._producer = Producer({
            "bootstrap.servers": self.config.brokers,
            "linger.ms": 20,
            "compression.type": "lz4",
            "enable.idempotence": True,      # no duplicates on retry
        })
        self._consumer_factory = Consumer
        self._consumer = None

    def publish(self, topic: str, key: str, event: dict[str, Any]) -> None:
        self._producer.produce(topic=topic, key=str(key), value=serialise(event))
        self._producer.poll(0)

    def flush(self) -> None:
        self._producer.flush(10)

    def _ensure_consumer(self, topics: list[str]):
        if self._consumer is None:
            self._consumer = self._consumer_factory({
                "bootstrap.servers": self.config.brokers,
                "group.id": self.config.consumer_group,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,  # commit only after a successful write
            })
            self._consumer.subscribe(topics)
        return self._consumer

    def consume(self, topics: list[str], max_messages: int = 500,
                timeout: float = 1.0) -> Iterator[dict[str, Any]]:
        consumer = self._ensure_consumer(topics)
        messages = consumer.consume(num_messages=max_messages, timeout=timeout)
        delivered = 0
        for message in messages:
            if message is None or message.error():
                if message is not None and message.error():
                    log.warning("kafka error: %s", message.error())
                continue
            yield deserialise(message.value())
            delivered += 1
        if delivered:
            consumer.commit(asynchronous=False)

    def close(self) -> None:
        self.flush()
        if self._consumer is not None:
            self._consumer.close()


def get_bus(config: StreamConfig | None = None) -> EventBus:
    config = config or STREAM
    if config.backend == "kafka":
        log.info("event bus: kafka @ %s", config.brokers)
        return KafkaEventBus(config)
    log.info("event bus: local files @ %s", config.directory)
    return FileEventBus(config)
