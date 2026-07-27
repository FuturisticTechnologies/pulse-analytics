"""Real-time layer: event bus, producer, consumer, stream processors and API.

The whole layer is written against the small :class:`streaming.bus.EventBus`
interface, with two implementations:

* ``local``  - append-only NDJSON files under ``data/stream``. No broker, no
  Docker, no ports. This is the default so the real-time story can be
  demonstrated on any machine in ten seconds.
* ``kafka``  - Redpanda / Apache Kafka / Azure Event Hubs, all of which speak
  the same protocol.

Producer and consumer code is byte-for-byte identical across the two. Switching
is one environment variable, which is the property that makes the local demo an
honest rehearsal of production rather than a different program.
"""
