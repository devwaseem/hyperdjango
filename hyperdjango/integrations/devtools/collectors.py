from __future__ import annotations

import logging
import re
from contextvars import ContextVar, Token
from threading import Lock
from time import perf_counter
from typing import Any

from django.db import connections

from hyperdjango.integrations.debug_toolbar.tracing import (
    RequestTrace,
    display_path,
    sanitize_value,
)


_active_trace: ContextVar[RequestTrace | None] = ContextVar(
    "hyperdjango_devtools_trace", default=None
)
_handler_lock = Lock()
_handler_installed = False
_MAX_LOGS = 200
_MAX_QUERIES = 500
_MAX_SQL_LENGTH = 8000


class _TraceLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        trace = _active_trace.get()
        if trace is None or len(trace.logs) >= _MAX_LOGS:
            return
        try:
            message = record.getMessage()
        except Exception:
            message = "<log message formatting failed>"
        trace.logs.append(
            {
                "level": record.levelname,
                "logger": record.name,
                "message": sanitize_value(message),
                "at_ms": round((perf_counter() - trace.started_at) * 1000, 3),
                "file": record.pathname,
                "display_file": display_path(record.pathname),
                "line": record.lineno,
                "function": record.funcName,
            }
        )
        trace.costs["log_records"] = len(trace.logs)
        trace.notify_update()


def _install_log_handler() -> None:
    global _handler_installed
    if _handler_installed:
        return
    with _handler_lock:
        if not _handler_installed:
            logging.getLogger().addHandler(_TraceLogHandler())
            _handler_installed = True


def _fingerprint(sql: str) -> str:
    normalized = re.sub(r"'(?:''|[^'])*'", "?", sql)
    normalized = re.sub(r'"(?:""|[^"])*"', "?", normalized)
    normalized = re.sub(r"\b\d+(?:\.\d+)?\b", "?", normalized)
    return " ".join(normalized.split()).lower()


def _bounded_sql(sql: Any) -> str:
    text = str(sql)
    if len(text) <= _MAX_SQL_LENGTH:
        return text
    return f"{text[: _MAX_SQL_LENGTH - 1]}…"


class RequestCollectors:
    def __init__(self, trace: RequestTrace) -> None:
        self.trace = trace
        self._log_token: Token[RequestTrace | None] | None = None
        self._sql_contexts: list[Any] = []
        self._closed = False

    def start(self) -> RequestCollectors:
        _install_log_handler()
        self._log_token = _active_trace.set(self.trace)
        for connection in connections.all():
            wrapper = connection.execute_wrapper(self._execute)
            wrapper.__enter__()
            self._sql_contexts.append(wrapper)
        return self

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for wrapper in reversed(self._sql_contexts):
            wrapper.__exit__(None, None, None)
        if self._log_token is not None:
            try:
                _active_trace.reset(self._log_token)
            except ValueError:
                _active_trace.set(None)

    def _execute(self, execute, sql, params, many, context):
        started = perf_counter()
        error = None
        try:
            return execute(sql, params, many, context)
        except BaseException as exc:
            error = f"{exc.__class__.__name__}: {exc}"
            raise
        finally:
            if len(self.trace.sql) < _MAX_QUERIES:
                duration = round((perf_counter() - started) * 1000, 3)
                connection = context.get("connection")
                query = {
                    "sql": _bounded_sql(sql),
                    "params": sanitize_value(params),
                    "many": bool(many),
                    "duration_ms": duration,
                    "at_ms": round((started - self.trace.started_at) * 1000, 3),
                    "alias": getattr(connection, "alias", "default"),
                    "transaction": bool(getattr(connection, "in_atomic_block", False)),
                    "phase": self.trace.phase_stack[-1]
                    if self.trace.phase_stack
                    else None,
                    "fingerprint": _fingerprint(str(sql)),
                }
                if error:
                    query["error"] = sanitize_value(error)
                self.trace.sql.append(query)
                self.trace.costs["sql_queries"] = len(self.trace.sql)
                self.trace.costs["sql_ms"] = round(
                    sum(item["duration_ms"] for item in self.trace.sql), 3
                )
                self.trace.notify_update()


def start_collectors(trace: RequestTrace) -> RequestCollectors:
    return RequestCollectors(trace).start()
