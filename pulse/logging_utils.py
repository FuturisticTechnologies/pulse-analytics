"""Consistent, quiet-by-default logging plus small console helpers."""
from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager

_CONFIGURED = False


def get_logger(name: str) -> logging.Logger:
    global _CONFIGURED
    if not _CONFIGURED:
        logging.basicConfig(
            level=os.environ.get("PULSE_LOG_LEVEL", "INFO").upper(),
            format="%(asctime)s | %(levelname)-7s | %(name)-24s | %(message)s",
            datefmt="%H:%M:%S",
        )
        _CONFIGURED = True
    return logging.getLogger(name)


@contextmanager
def timed(logger: logging.Logger, label: str):
    """Log how long a pipeline step took - used by every ETL stage."""
    start = time.perf_counter()
    logger.info("%s ...", label)
    try:
        yield
    finally:
        logger.info("%s done in %.2fs", label, time.perf_counter() - start)


def banner(title: str, width: int = 72) -> str:
    return "\n".join(["=" * width, title.center(width), "=" * width])
