from __future__ import annotations

from contextvars import ContextVar
from typing import Any


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
