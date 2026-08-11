from __future__ import annotations

import json
import inspect
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Iterator

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest


TRACE_ATTRIBUTE = "_hyperdjango_debug_toolbar_trace"
MAX_REPR_LENGTH = 160
MAX_CONTENT_LENGTH = 1000
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


def _callable_mode(value: Any) -> str:
    if inspect.isasyncgenfunction(value):
        return "async stream"
    if inspect.isgeneratorfunction(value):
        return "stream"
    if inspect.iscoroutinefunction(value):
        return "async"
    return "sync"


def display_path(file_name: str | Path) -> str:
    path = Path(file_name).resolve()
    roots: list[Path] = []
    try:
        base_dir = getattr(settings, "BASE_DIR", None)
    except ImproperlyConfigured:
        base_dir = None
    if base_dir:
        roots.append(Path(base_dir).resolve())
    try:
        from hyperdjango.conf import get_frontend_dir

        roots.append(get_frontend_dir().resolve().parent)
    except RuntimeError:
        pass
    roots.append(Path.cwd().resolve())
    for root in roots:
        try:
            return str(path.relative_to(root)) or "."
        except ValueError:
            continue
    if "site-packages" in path.parts:
        index = path.parts.index("site-packages")
        return str(Path(*path.parts[index + 1 :]))
    return str(Path(*path.parts[-4:]))


def _source_location(value: Any) -> dict[str, Any] | None:
    try:
        file_name = inspect.getsourcefile(value) or inspect.getfile(value)
        _, line = inspect.getsourcelines(value)
    except (OSError, TypeError):
        return None
    return {
        "file": file_name,
        "display_file": display_path(file_name),
        "line": line,
        "symbol": getattr(value, "__qualname__", getattr(value, "__name__", None)),
    }


def _template_source(template_name: str) -> dict[str, Any] | None:
    try:
        from django.template.loader import get_template

        template = get_template(template_name)
        origin = getattr(template, "origin", None) or getattr(
            getattr(template, "template", None), "origin", None
        )
        file_name = getattr(origin, "name", None)
    except Exception:
        return None
    return (
        {
            "file": str(file_name),
            "display_file": display_path(file_name),
            "line": 1,
            "symbol": template_name,
        }
        if file_name
        else None
    )


def _route_details(page: Any) -> dict[str, Any]:
    page_class = page.__class__
    page_source = _source_location(page_class)
    page_file = Path(page_source["file"]).resolve() if page_source else None
    directory = page_file.parent if page_file else None
    try:
        from hyperdjango.conf import get_frontend_dir, is_dev_env

        frontend_dir = get_frontend_dir().resolve()
        relative_directory = (
            str(directory.relative_to(frontend_dir)) if directory else None
        )
        asset_environment = "development" if is_dev_env() else "production"
    except (OSError, RuntimeError, ValueError):
        frontend_dir = None
        relative_directory = None
        asset_environment = "unknown"

    template_name = None
    template_source = None
    try:
        template_name = page.get_template_name()
        template_source = _template_source(template_name)
    except (AttributeError, FileNotFoundError, OSError, RuntimeError, ValueError):
        pass

    layouts = []
    for cls in page_class.__mro__[1:]:
        if cls.__module__.startswith(("hyperdjango.", "django.")):
            continue
        source = _source_location(cls)
        if source is None or (page_file and Path(source["file"]).resolve() == page_file):
            continue
        layouts.append(
            {
                "class": _qualified_name(cls),
                "source": source,
            }
        )

    asset_entries = []
    seen_entries: set[Path] = set()
    for cls in page_class.__mro__:
        if cls.__module__.startswith("django.") or (
            cls.__module__.startswith("hyperdjango.")
            and not cls.__module__.startswith("hyperdjango.dynamic.")
        ):
            continue
        try:
            base_path = cls._get_base_path().resolve()
        except (AttributeError, OSError, RuntimeError, TypeError):
            continue
        for file_name, section in (
            ("entry.head.js", "head"),
            ("entry.head.ts", "head"),
            ("entry.js", "body"),
            ("entry.ts", "body"),
        ):
            entry_path = base_path / file_name
            if not entry_path.is_file() or entry_path in seen_entries:
                continue
            seen_entries.add(entry_path)
            asset_entries.append(
                {
                    "scope": "route" if cls is page_class else "layout",
                    "section": section,
                    "file": display_path(entry_path),
                    "relative_file": (
                        str(entry_path.relative_to(frontend_dir.parent))
                        if frontend_dir and frontend_dir.parent in entry_path.parents
                        else file_name
                    ),
                    "source": {
                        "file": str(entry_path),
                        "display_file": display_path(entry_path),
                        "line": 1,
                        "symbol": file_name,
                    },
                }
            )

    resolved_assets = []
    for attribute, section in (
        ("stylesheets", "stylesheet"),
        ("preload_imports", "preload"),
        ("head_imports", "head"),
        ("body_imports", "body"),
    ):
        for tag in getattr(page, attribute, []):
            resolved_assets.append(
                {
                    "section": section,
                    "type": tag.__class__.__name__.removesuffix("Tag"),
                    "url": str(tag.src),
                }
            )

    diagnostics = []
    if page_file is None or not page_file.is_file():
        diagnostics.append(
            {"severity": "error", "message": "Page source file could not be resolved."}
        )
    if template_name and template_source is None:
        diagnostics.append(
            {
                "severity": "warning",
                "message": f"Template source could not be resolved: {template_name}",
            }
        )

    return {
        "directory": display_path(directory) if directory else None,
        "relative_directory": relative_directory,
        "page_file": display_path(page_file) if page_file else None,
        "template": {"name": template_name, "source": template_source},
        "layouts": layouts,
        "assets": {
            "environment": asset_environment,
            "entries": asset_entries,
            "resolved": resolved_assets,
        },
        "diagnostics": diagnostics,
    }


def _is_sensitive(name: str) -> bool:
    normalized = name.lower().replace("-", "_")
    return any(fragment in normalized for fragment in SENSITIVE_FRAGMENTS)


def _cap(value: str, *, max_length: int = MAX_REPR_LENGTH) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 1]}…"


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


def sanitize_mapping(value: dict[Any, Any]) -> dict[str, Any]:
    """Sanitize every mapping entry without applying the collection-size cap."""
    return {
        _cap(str(item_key)): sanitize_value(item_value, key=str(item_key), depth=1)
        for item_key, item_value in value.items()
    }


@dataclass
class RequestTrace:
    request: dict[str, Any]
    started_at: float = field(default_factory=perf_counter, repr=False)
    route: dict[str, Any] = field(default_factory=dict)
    action: dict[str, Any] = field(default_factory=dict)
    renders: list[dict[str, Any]] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    timings: list[dict[str, Any]] = field(default_factory=list)
    exceptions: list[dict[str, str]] = field(default_factory=list)
    response: dict[str, Any] = field(default_factory=dict)
    sql: list[dict[str, Any]] = field(default_factory=list)
    logs: list[dict[str, Any]] = field(default_factory=list)
    lifecycle: list[dict[str, Any]] = field(default_factory=list)
    client: dict[str, Any] = field(default_factory=dict)
    costs: dict[str, Any] = field(default_factory=dict)
    phase_stack: list[str] = field(default_factory=list, repr=False)
    on_update: Callable[[dict[str, Any]], None] | None = field(default=None, repr=False)

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
            "sql": self.sql,
            "logs": self.logs,
            "lifecycle": self.lifecycle,
            "client": self.client,
            "costs": self.costs,
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

    def notify_update(self) -> None:
        if self.on_update is None:
            return
        try:
            self.on_update(self.snapshot())
        except Exception:
            # Debug instrumentation must never affect the observed request.
            return

    def add_timing(
        self,
        phase: str,
        started: float,
        *,
        finished: float | None = None,
        depth: int = 1,
        parent: str = "request",
    ) -> dict[str, Any]:
        finished = perf_counter() if finished is None else finished
        start_ms = round(max(0.0, started - self.started_at) * 1000, 3)
        end_ms = round(max(0.0, finished - self.started_at) * 1000, 3)
        timing = {
            "phase": phase,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": round(max(0.0, finished - started) * 1000, 3),
            "depth": depth,
            "parent": parent,
        }
        self.timings.append(timing)
        return timing

    def add_lifecycle(self, kind: str, **details: Any) -> None:
        self.lifecycle.append(
            {
                "kind": kind,
                "at_ms": round((perf_counter() - self.started_at) * 1000, 3),
                **sanitize_value(details),
            }
        )


def start_trace(request: HttpRequest) -> RequestTrace:
    trace = RequestTrace(
        request={
            "method": str(request.method),
            "path": str(request.path),
        }
    )
    setattr(request, TRACE_ATTRIBUTE, trace)
    trace.add_lifecycle("request started", method=request.method, path=request.path)
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
        "namespace": getattr(resolver_match, "namespace", None),
        "pattern": getattr(resolver_match, "route", None),
        "page_class": _qualified_name(page),
        "handler": handler,
        "parameters": sanitize_value(route_params),
        "source": _source_location(page.__class__),
        "details": _route_details(page),
    }
    method_name = handler.split(":", 1)[-1] if handler.startswith("action:") else handler
    method = getattr(page, method_name, None)
    if method is not None:
        trace.route["handler_source"] = _source_location(method)
        trace.route["handler_mode"] = _callable_mode(method)
    trace.add_lifecycle(
        "route resolved", handler=handler, page=trace.route["page_class"]
    )


def record_action(
    request: HttpRequest,
    *,
    name: str,
    target: str,
    arguments: dict[str, Any],
    handler: Any | None = None,
) -> None:
    trace = get_trace(request)
    if trace is not None:
        trace.action = {
            "name": name,
            "target": target or None,
            "arguments": sanitize_value(arguments),
            "source": _source_location(handler) if handler is not None else None,
            "mode": _callable_mode(handler) if handler is not None else None,
        }
        trace.add_lifecycle("action dispatched", name=name, target=target or None)


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
        "source": _template_source(template),
        "_started_at": perf_counter(),
    }
    trace.renders.append(event)
    return event


def record_render_output(
    request: HttpRequest,
    event: dict[str, Any] | None,
    html: str,
    context: dict[str, Any] | None = None,
) -> None:
    trace = get_trace(request)
    if trace is None or event is None:
        return
    size = len(html.encode())
    started = event.pop("_started_at", None)
    if isinstance(started, (int, float)):
        event["duration_ms"] = round((perf_counter() - started) * 1000, 3)
    event["bytes"] = size
    event["context_keys"] = len(context or {})
    trace.costs["render_bytes"] = trace.costs.get("render_bytes", 0) + size
    trace.costs["render_operations"] = len(trace.renders)
    trace.costs["render_ms"] = round(
        sum(float(item.get("duration_ms", 0)) for item in trace.renders), 3
    )


def record_exception(request: HttpRequest, exc: BaseException, *, phase: str) -> None:
    trace = get_trace(request)
    if trace is None:
        return
    item = {
        "phase": phase,
        "type": _qualified_name(exc),
        "message": _cap(str(exc) or repr(exc)),
        "frames": _exception_frames(exc),
    }
    template_debug = getattr(exc, "template_debug", None)
    if isinstance(template_debug, dict):
        item["template"] = sanitize_value(
            {
                key: template_debug.get(key)
                for key in ("name", "message", "line", "before", "during", "after")
                if template_debug.get(key) is not None
            }
        )
    if item not in trace.exceptions:
        trace.exceptions.append(item)
        trace.add_lifecycle("exception", phase=phase, type=item["type"])


def _exception_frames(exc: BaseException) -> list[dict[str, Any]]:
    extracted = traceback.extract_tb(exc.__traceback__)
    frames: list[dict[str, Any]] = []
    for index, (frame, line_number) in enumerate(traceback.walk_tb(exc.__traceback__)):
        frames.append(
            {
                "file": frame.f_code.co_filename,
                "display_file": display_path(frame.f_code.co_filename),
                "line": line_number,
                "function": frame.f_code.co_name,
                "source": extracted[index].line or "" if index < len(extracted) else "",
                "locals": {
                    name: sanitize_value(value, key=name)
                    for name, value in list(frame.f_locals.items())[
                        :MAX_COLLECTION_ITEMS
                    ]
                },
            }
        )
        if len(frames) >= 20:
            break
    return frames


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
        "focus",
        "swap_delay",
        "settle_delay",
        "strict_targets",
        "transition",
        "redirect_to",
        "status",
    ):
        value = getattr(item, attribute, None)
        if attribute == "transition" and value is False:
            continue
        if value not in (None, ""):
            metadata[attribute] = sanitize_value(value, key=attribute)

    for attribute in ("content", "html", "js"):
        if hasattr(item, attribute):
            value = getattr(item, attribute)
            if value not in (None, ""):
                metadata[attribute] = (
                    _cap(value, max_length=MAX_CONTENT_LENGTH)
                    if isinstance(value, str)
                    else sanitize_value(value, key=attribute)
                )

    for attribute in ("payload", "value", "values", "signals", "toasts", "headers"):
        if hasattr(item, attribute):
            value = getattr(item, attribute)
            if value not in (None, {}, []):
                metadata[attribute] = sanitize_value(value, key=attribute)

    labels = {
        "url": "URL",
        "push_url": "push URL",
        "replace_url": "replace URL",
        "redirect_to": "redirect",
        "src": "source",
        "swap_delay": "swap delay",
        "settle_delay": "settle delay",
        "strict_targets": "strict targets",
    }
    metadata["details"] = [
        {"label": labels.get(key, key.replace("_", " ")), "value": value}
        for key, value in metadata.items()
        if key not in {"type", "target", "swap", "content", "html", "js"}
    ]
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
        item = _item_metadata(result)
        item["content_type"] = result.get("Content-Type", "")
        item["details"].append({"label": "content type", "value": item["content_type"]})
        return {
            "kind": result.__class__.__name__,
            "streaming": bool(getattr(result, "streaming", False)),
            "item_types": [result.__class__.__name__],
            "items": [item],
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
            "items": [_item_metadata(result)],
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
            "iteration_status": "not started",
            "note": "Stream iteration has not started.",
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
        described = describe_result(result)
        if described.get("streaming"):
            described["request_id"] = request.headers.get("X-Hyper-Request-ID")
            described["resume_from"] = request.headers.get("Last-Event-ID")
        trace.results.append(described)
        trace.add_lifecycle(
            "result prepared",
            result_kind=described["kind"],
            streaming=described["streaming"],
        )


def record_stream_item(request: HttpRequest | None, item: Any) -> None:
    trace = get_trace(request)
    if trace is None or not trace.results:
        return
    result = trace.results[-1]
    if not result.get("streaming"):
        return
    if result.get("iteration_status") in (None, "not started"):
        result["items"] = []
        result["item_types"] = []
    metadata = _item_metadata(item)
    sequence = len(result["items"]) + 1
    now_ms = round((perf_counter() - trace.started_at) * 1000, 3)
    previous_ms = result["items"][-1].get("at_ms") if result["items"] else None
    try:
        from hyperdjango.runtime.responses import serialize_action_item

        event_name, payload = serialize_action_item(item)
        payload_bytes = len(json.dumps(payload, default=str).encode())
    except Exception:
        event_name, payload_bytes = metadata["type"], 0
    metadata.update(
        {
            "sequence": sequence,
            "event": event_name,
            "event_id": (
                f"{result['request_id']}:{sequence}"
                if result.get("request_id")
                else None
            ),
            "at_ms": now_ms,
            "gap_ms": round(now_ms - previous_ms, 3)
            if previous_ms is not None
            else None,
            "payload_bytes": payload_bytes,
        }
    )
    resume_index = 0
    resume_from = result.get("resume_from") or ""
    if result.get("request_id") and resume_from.startswith(f"{result['request_id']}:"):
        try:
            resume_index = int(resume_from.rsplit(":", 1)[1])
        except ValueError:
            resume_index = 0
    metadata["delivered"] = sequence > resume_index
    result["items"].append(metadata)
    result["item_types"].append(metadata["type"])
    result["iteration_status"] = "streaming"
    result["note"] = "Stream iteration is in progress."
    trace.costs["sse_items"] = trace.costs.get("sse_items", 0) + 1
    trace.costs["sse_payload_bytes"] = (
        trace.costs.get("sse_payload_bytes", 0) + payload_bytes
    )
    trace.costs.setdefault("time_to_first_sse_item_ms", now_ms)
    trace.add_lifecycle("SSE item", sequence=sequence, event=event_name)
    trace.notify_update()


def record_stream_finished(
    request: HttpRequest,
    *,
    status: str,
    exception: BaseException | None = None,
) -> None:
    trace = get_trace(request)
    if trace is None or not trace.results:
        return
    result = trace.results[-1]
    if not result.get("streaming"):
        return
    if result.get("iteration_status") in (None, "not started"):
        result["items"] = []
        result["item_types"] = []
    result["iteration_status"] = status
    result["note"] = {
        "completed": "Stream iteration completed.",
        "closed": "Stream iteration closed before completion.",
        "failed": "Stream iteration failed.",
    }.get(status, status)
    if exception is not None:
        record_exception(request, exception, phase="stream iteration")
    trace.add_lifecycle("stream finished", status=status, items=len(result["items"]))


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
    parent = trace.phase_stack[-1] if trace.phase_stack else "request"
    depth = len(trace.phase_stack) + 1
    trace.phase_stack.append(phase)
    trace.add_lifecycle("phase started", phase=phase)
    try:
        yield
    finally:
        timing = trace.add_timing(phase, started, depth=depth, parent=parent)
        if trace.phase_stack:
            trace.phase_stack.pop()
        trace.add_lifecycle(
            "phase finished", phase=phase, duration_ms=timing["duration_ms"]
        )
        if event is not None:
            event["duration_ms"] = timing["duration_ms"]
