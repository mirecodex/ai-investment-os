"""Structured logging with per-run correlation.

Every analysis run gets a ``run_id`` bound into contextvars so that log lines
emitted anywhere in the graph (analysts, rule engine, delivery) can be joined
back into one trace. See docs/fase-4-engineering/06-observability.md.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import structlog


def configure_logging(*, json_output: bool = False, level: str = "INFO") -> None:
    renderer: structlog.typing.Processor
    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]


@contextmanager
def bind_run_context(**extra: Any) -> Iterator[str]:
    """Bind a fresh run_id (plus caller context, e.g. ticker) for the scope."""
    run_id = uuid.uuid4().hex[:12]
    tokens = structlog.contextvars.bind_contextvars(run_id=run_id, **extra)
    try:
        yield run_id
    finally:
        structlog.contextvars.reset_contextvars(**tokens)
