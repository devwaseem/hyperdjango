from __future__ import annotations

import copy
import logging
import os
from contextvars import ContextVar
from typing import Any


SUPERVISED_RUNSERVER_ENV = "HYPER_DJANGO_RUNSERVER_SUPERVISED"
_request_log_context: ContextVar[dict[str, Any] | None] = ContextVar(
    "hyperdjango_request_log_context", default=None
)


def set_request_log_context(
    *,
    duration_ms: float,
    trace_url: str,
    action: str | None = None,
    sql_queries: int = 0,
    sql_ms: float = 0,
    render_ms: float = 0,
) -> None:
    _request_log_context.set(
        {
            "duration_ms": duration_ms,
            "trace_url": trace_url,
            "action": action,
            "sql_queries": sql_queries,
            "sql_ms": sql_ms,
            "render_ms": render_ms,
        }
    )


def consume_request_log_context() -> dict[str, Any] | None:
    context = _request_log_context.get()
    _request_log_context.set(None)
    return context


def enrich_request_log_record(record: logging.LogRecord) -> logging.LogRecord:
    if record.name != "django.server":
        return record
    context = consume_request_log_context()
    if not context:
        return record

    action = f" · action {context['action']}" if context.get("action") else ""
    sql = (
        f" · {context['sql_queries']} SQL/{context['sql_ms']:.1f} ms"
        if context.get("sql_queries")
        else ""
    )
    render = (
        f" · render {context['render_ms']:.1f} ms"
        if context.get("render_ms")
        else ""
    )
    enriched = copy.copy(record)
    enriched.msg = (
        f"{record.msg} · {context['duration_ms']:.1f} ms"
        f"{action}{sql}{render} · {context['trace_url']}"
    )
    return enriched


class SupervisedRequestLogFilter(logging.Filter):
    """Add request diagnostics inside a supervised Django reload child."""

    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        return enrich_request_log_record(record)


def install_supervised_request_log_filter() -> None:
    if os.environ.get(SUPERVISED_RUNSERVER_ENV) != "true":
        return
    logger = logging.getLogger("django.server")
    if not any(isinstance(item, SupervisedRequestLogFilter) for item in logger.filters):
        logger.addFilter(SupervisedRequestLogFilter())
