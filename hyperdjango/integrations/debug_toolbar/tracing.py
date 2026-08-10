from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Iterator

from django.http import HttpRequest


TRACE_ATTRIBUTE = "_hyperdjango_debug_toolbar_trace"
MAX_REPR_LENGTH = 160
MAX_COLLECTION_ITEMS = 10
SENSITIVE_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "csrf",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
)


def _qualified_name(value: type[Any] | Any) -> str:
    cls = value if isinstance(value, type) else value.__class__
    return f"{cls.__module__}.{cls.__qualname__}"


def _is_sensitive(name: str) -> bool:
    normalized = name.lower().replace("-", "_")
    return any(fragment in normalized for fragment in SENSITIVE_FRAGMENTS)


def _cap(value: str) -> str:
    if len(value) <= MAX_REPR_LENGTH:
        return value
    return f"{value[: MAX_REPR_LENGTH - 1]}…"


def sanitize_value(value: Any, *, key: str = "", depth: int = 0) -> Any:
    if key and _is_sensitive(key):
        return "[redacted]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _cap(value)
    if isinstance(value, dict) and depth < 2:
        items = list(value.items())[:MAX_COLLECTION_ITEMS]
        sanitized = {
            _cap(str(item_key)): sanitize_value(
                item_value, key=str(item_key), depth=depth + 1
            )
            for item_key, item_value in items
        }
        if len(value) > MAX_COLLECTION_ITEMS:
            sanitized["…"] = f"{len(value) - MAX_COLLECTION_ITEMS} more keys"
        return sanitized
    if isinstance(value, (list, tuple)) and depth < 2:
        values = [
            sanitize_value(item, depth=depth + 1)
            for item in value[:MAX_COLLECTION_ITEMS]
        ]
        if len(value) > MAX_COLLECTION_ITEMS:
            values.append(f"… {len(value) - MAX_COLLECTION_ITEMS} more items")
        return values
    try:
        return _cap(repr(value))
    except Exception:
        return f"<{_qualified_name(value)} repr failed>"


@dataclass
class RequestTrace:
    request: dict[str, Any]
    route: dict[str, Any] = field(default_factory=dict)
    action: dict[str, Any] = field(default_factory=dict)
    renders: list[dict[str, Any]] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    timings: list[dict[str, Any]] = field(default_factory=list)
    exceptions: list[dict[str, str]] = field(default_factory=list)
    response: dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "route": self.route,
            "action": self.action,
            "renders": self.renders,
            "results": self.results,
            "timings": self.timings,
            "exceptions": self.exceptions,
            "response": self.response,
            "is_hyperdjango": bool(self.route),
            "total_ms": round(
                sum(
                    timing["duration_ms"]
                    for timing in self.timings
                    if timing["phase"] == "dispatch"
                ),
                3,
            ),
        }


def start_trace(request: HttpRequest) -> RequestTrace:
    trace = RequestTrace(
        request={
            "method": str(request.method),
            "path": str(request.path),
        }
    )
    setattr(request, TRACE_ATTRIBUTE, trace)
    return trace


def clear_trace(request: HttpRequest, trace: RequestTrace) -> None:
    if getattr(request, TRACE_ATTRIBUTE, None) is trace:
        delattr(request, TRACE_ATTRIBUTE)


def get_trace(request: HttpRequest | None) -> RequestTrace | None:
    if request is None:
        return None
    trace = getattr(request, TRACE_ATTRIBUTE, None)
    return trace if isinstance(trace, RequestTrace) else None


def record_dispatch(
    request: HttpRequest,
    page: Any,
    *,
    handler: str,
    route_params: dict[str, Any],
) -> None:
    trace = get_trace(request)
    if trace is None:
        return
    resolver_match = getattr(request, "resolver_match", None)
    trace.route = {
        "name": getattr(resolver_match, "view_name", None),
        "pattern": getattr(resolver_match, "route", None),
        "page_class": _qualified_name(page),
        "handler": handler,
        "parameters": sanitize_value(route_params),
    }


def record_action(
    request: HttpRequest, *, name: str, target: str, arguments: dict[str, Any]
) -> None:
    trace = get_trace(request)
    if trace is not None:
        trace.action = {
            "name": name,
            "target": target or None,
            "arguments": sanitize_value(arguments),
        }


def record_render(
    request: HttpRequest,
    *,
    kind: str,
    template: str,
    block: str | None = None,
    relative_template: str | None = None,
) -> dict[str, Any] | None:
    trace = get_trace(request)
    if trace is None:
        return None
    event = {
        "kind": kind,
        "template": template,
        "block": block,
        "relative_template": relative_template,
    }
    trace.renders.append(event)
    return event


def record_exception(request: HttpRequest, exc: BaseException, *, phase: str) -> None:
    trace = get_trace(request)
    if trace is None:
        return
    item = {
        "phase": phase,
        "type": _qualified_name(exc),
        "message": _cap(str(exc) or repr(exc)),
    }
    if item not in trace.exceptions:
        trace.exceptions.append(item)


def _item_metadata(item: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {"type": item.__class__.__name__}
    for attribute in (
        "target",
        "swap",
        "push_url",
        "replace_url",
        "url",
        "src",
        "name",
    ):
        value = getattr(item, attribute, None)
        if value not in (None, ""):
            metadata[attribute] = sanitize_value(value, key=attribute)
    return metadata


def describe_result(result: Any) -> dict[str, Any]:
    from django.http.response import HttpResponseBase

    from hyperdjango.actions import (
        ActionResult,
        Actions,
        Delete,
        Event,
        History,
        HTML,
        LoadJS,
        Redirect,
        Toast,
    )
    from hyperdjango.integrations.alpine.actions import Signal, Signals

    if isinstance(result, HttpResponseBase):
        return {
            "kind": result.__class__.__name__,
            "streaming": bool(getattr(result, "streaming", False)),
            "item_types": [result.__class__.__name__],
            "items": [
                {
                    "type": result.__class__.__name__,
                    "status": result.status_code,
                    "content_type": result.get("Content-Type", ""),
                }
            ],
        }

    if isinstance(result, ActionResult):
        item_types = []
        if result.redirect_to:
            item_types.append("Redirect")
        else:
            if result.signals:
                item_types.append("Signals")
            if result.toasts:
                item_types.extend("Toast" for _ in result.toasts)
            if result.push_url or result.replace_url:
                item_types.append("History")
            if result.html is not None:
                item_types.append("HTML")
            if result.js:
                item_types.append("LoadJS")
        return {
            "kind": "ActionResult",
            "streaming": False,
            "item_types": item_types,
            "items": [
                {
                    "type": "ActionResult",
                    "target": result.target,
                    "swap": result.swap,
                    "push_url": result.push_url,
                    "replace_url": result.replace_url,
                    "redirect_to": result.redirect_to,
                    "status": result.status,
                }
            ],
        }
    if isinstance(result, Actions):
        items = list(result.items)
        return {
            "kind": "Actions",
            "streaming": False,
            "item_types": [item.__class__.__name__ for item in items],
            "items": [_item_metadata(item) for item in items],
        }
    if isinstance(
        result,
        (Signal, Signals, HTML, Toast, Event, Delete, Redirect, History, LoadJS),
    ):
        return {
            "kind": result.__class__.__name__,
            "streaming": False,
            "item_types": [result.__class__.__name__],
            "items": [_item_metadata(result)],
        }
    if isinstance(result, (list, tuple)):
        return {
            "kind": result.__class__.__name__,
            "streaming": False,
            "item_types": [item.__class__.__name__ for item in result],
            "items": [_item_metadata(item) for item in result],
        }
    if isinstance(result, str):
        return {
            "kind": "HTML string",
            "streaming": False,
            "item_types": ["HTML"],
            "items": [],
        }
    if hasattr(result, "__aiter__") or (
        hasattr(result, "__iter__")
        and not isinstance(result, (str, bytes, bytearray, dict))
    ):
        return {
            "kind": _qualified_name(result),
            "streaming": True,
            "item_types": ["Unknown until stream iteration"],
            "items": [],
            "note": "The stream was not consumed for debugging.",
        }
    return {
        "kind": result.__class__.__name__,
        "streaming": False,
        "item_types": [result.__class__.__name__],
        "items": [],
    }


def record_result(request: HttpRequest, result: Any) -> None:
    trace = get_trace(request)
    if trace is not None:
        trace.results.append(describe_result(result))


def record_response(request: HttpRequest, response: Any) -> None:
    trace = get_trace(request)
    if trace is None:
        return
    trace.response = {
        "status": getattr(response, "status_code", None),
        "content_type": response.get("Content-Type", "")
        if hasattr(response, "get")
        else "",
        "streaming": bool(getattr(response, "streaming", False)),
    }


@contextmanager
def operation(
    request: HttpRequest | None,
    phase: str,
    event: dict[str, Any] | None = None,
) -> Iterator[None]:
    trace = get_trace(request)
    if trace is None:
        yield
        return
    started = perf_counter()
    try:
        yield
    finally:
        duration = round((perf_counter() - started) * 1000, 3)
        trace.timings.append({"phase": phase, "duration_ms": duration})
        if event is not None:
            event["duration_ms"] = duration
