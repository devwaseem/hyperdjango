from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterable, AsyncIterator, Iterable, Iterator
from queue import Queue
from threading import Thread
from typing import Any

from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.utils.cache import patch_vary_headers

from hyperdjango.actions import (
    ActionItem,
    Actions,
    ActionResult,
    Delete,
    Event,
    HTML,
    History,
    LoadJS,
    Redirect,
    Signal,
    Signals,
    Toast,
)
from hyperdjango.integrations.debug_toolbar.tracing import record_stream_item


ACTION_VARY_HEADERS = [
    "X-Hyper-Action",
    "X-Hyper-Target",
    "X-Hyper-Data",
    "X-Requested-With",
    "X-Hyper-Request-ID",
    "Last-Event-ID",
]

_ITERATION_DONE = object()
_VALID_SSE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def ensure_action_response_headers(response: HttpResponse) -> HttpResponse:
    patch_vary_headers(response, ACTION_VARY_HEADERS)
    response["Cache-Control"] = "no-store, no-cache, max-age=0, must-revalidate"
    response["Pragma"] = "no-cache"
    return response


def to_action_http_response(
    result: Any, *, request: HttpRequest | None = None
) -> HttpResponse:
    items, status, headers = normalize_action_result(result)
    items = _observe_action_items(items, request=request)
    event_id_prefix, skip_events = _sse_resume_context(request)
    streaming_content: Iterable[str] | AsyncIterator[str]
    if _is_asgi_request(request):
        streaming_content = stream_action_sse_async(
            items, event_id_prefix=event_id_prefix, skip_events=skip_events
        )
    else:
        streaming_content = stream_action_sse_sync(
            items, event_id_prefix=event_id_prefix, skip_events=skip_events
        )
    response = StreamingHttpResponse(
        streaming_content,
        status=status,
        content_type="text/event-stream",
    )
    response["X-Accel-Buffering"] = "no"
    for key, value in headers.items():
        response[key] = value
    return ensure_action_response_headers(response)


def _observe_action_items(
    items: Iterable[ActionItem] | AsyncIterable[ActionItem],
    *,
    request: HttpRequest | None,
) -> Iterable[ActionItem] | AsyncIterable[ActionItem]:
    if isinstance(items, AsyncIterable):

        async def observe_async() -> AsyncIterator[ActionItem]:
            async for item in items:
                record_stream_item(request, item)
                yield item

        return observe_async()

    def observe_sync() -> Iterator[ActionItem]:
        for item in items:
            record_stream_item(request, item)
            yield item

    return observe_sync()


def _action_error_event(status: int, message: str) -> tuple[str, dict[str, Any]]:
    return "error", {"status": status, "message": message}


def to_action_exception_response(
    status: int, message: str, *, request: HttpRequest | None = None
) -> HttpResponse:
    event_id_prefix, skip_events = _sse_resume_context(request)
    response = StreamingHttpResponse(
        stream_action_exception_sse_async(
            status,
            message,
            event_id_prefix=event_id_prefix,
            skip_events=skip_events,
        )
        if _is_asgi_request(request)
        else stream_action_exception_sse_sync(
            status,
            message,
            event_id_prefix=event_id_prefix,
            skip_events=skip_events,
        ),
        status=status,
        content_type="text/event-stream",
    )
    response["X-Accel-Buffering"] = "no"
    return ensure_action_response_headers(response)


def normalize_action_result(
    result: Any,
) -> tuple[Iterable[ActionItem] | AsyncIterable[ActionItem], int, dict[str, str]]:
    if isinstance(result, ActionResult):
        return compile_action_result(result), result.status, result.headers
    if isinstance(result, Actions):
        return result, 200, {}
    if is_action_item(result):
        return [result], 200, {}
    if is_action_item_iterable(result):
        return result, 200, {}
    if is_action_item_async_iterable(result):
        return result, 200, {}
    raise TypeError(f"Unsupported action result type: {type(result).__name__}")


def is_action_item(value: Any) -> bool:
    return isinstance(
        value,
        (
            Signal,
            Signals,
            HTML,
            Toast,
            Event,
            Delete,
            Redirect,
            History,
            LoadJS,
        ),
    )


def is_action_item_iterable(value: Any) -> bool:
    if isinstance(value, (str, bytes, bytearray, dict, ActionResult)):
        return False
    return isinstance(value, Iterable)


def is_action_item_async_iterable(value: Any) -> bool:
    return isinstance(value, AsyncIterable)


def compile_action_result(result: ActionResult) -> list[ActionItem]:
    items: list[ActionItem] = []
    if result.redirect_to:
        items.append(Redirect(url=result.redirect_to))
        return items
    if result.signals:
        items.append(Signals(values=result.signals))
    if result.toasts:
        items.extend(Toast(payload=toast) for toast in result.toasts)
    if result.push_url or result.replace_url:
        items.append(History(push_url=result.push_url, replace_url=result.replace_url))
    if result.html is not None:
        items.append(
            HTML(
                content=result.html,
                target=result.target,
                swap=result.swap or "outer",
                transition=result.transition,
                focus=result.focus,
                swap_delay=result.swap_delay,
                settle_delay=result.settle_delay,
                strict_targets=result.strict_targets,
            )
        )
    if result.js:
        items.append(LoadJS(src=result.js))
    return items


def stream_action_sse(
    items: Iterable[ActionItem], *, event_id_prefix: str = "", skip_events: int = 0
) -> Iterator[str]:
    redirect_seen = False
    event_index = 0
    for item in items:
        event_index += 1
        event_name, payload = serialize_action_item(item)
        if event_index > skip_events:
            yield _format_sse_event(
                event_name, payload, _event_id(event_id_prefix, event_index)
            )
        if isinstance(item, Redirect):
            redirect_seen = True
            break
    if not redirect_seen:
        event_index += 1
        if event_index > skip_events:
            yield _format_sse_event(
                "end", {}, _event_id(event_id_prefix, event_index)
            )


def stream_action_sse_sync(
    items: Iterable[ActionItem] | AsyncIterable[ActionItem],
    *,
    event_id_prefix: str = "",
    skip_events: int = 0,
) -> Iterator[str]:
    if isinstance(items, AsyncIterable):
        return _stream_action_sse_sync_from_async(
            items, event_id_prefix=event_id_prefix, skip_events=skip_events
        )
    return stream_action_sse(
        items, event_id_prefix=event_id_prefix, skip_events=skip_events
    )


async def stream_action_sse_async(
    items: Iterable[ActionItem] | AsyncIterable[ActionItem],
    *,
    event_id_prefix: str = "",
    skip_events: int = 0,
) -> AsyncIterator[str]:
    redirect_seen = False
    event_index = 0
    if isinstance(items, AsyncIterable):
        async_iterator = items.__aiter__()
        while True:
            item = await _next_async_action_item(async_iterator)
            if item is _ITERATION_DONE:
                break
            event_index += 1
            event_name, payload = serialize_action_item(item)
            if event_index > skip_events:
                yield _format_sse_event(
                    event_name, payload, _event_id(event_id_prefix, event_index)
                )
            if isinstance(item, Redirect):
                redirect_seen = True
                break
    else:
        iterator = iter(items)
        while True:
            item = await sync_to_async(_next_action_item, thread_sensitive=True)(
                iterator
            )
            if item is _ITERATION_DONE:
                break
            event_index += 1
            event_name, payload = serialize_action_item(item)
            if event_index > skip_events:
                yield _format_sse_event(
                    event_name, payload, _event_id(event_id_prefix, event_index)
                )
            if isinstance(item, Redirect):
                redirect_seen = True
                break

    if not redirect_seen:
        event_index += 1
        if event_index > skip_events:
            yield _format_sse_event(
                "end", {}, _event_id(event_id_prefix, event_index)
            )


def _stream_action_sse_sync_from_async(
    items: AsyncIterable[ActionItem],
    *,
    event_id_prefix: str = "",
    skip_events: int = 0,
) -> Iterator[str]:
    queue: Queue[tuple[str, str | BaseException | None]] = Queue()

    def producer() -> None:
        try:
            asyncio.run(
                _produce_action_sse(
                    items,
                    queue,
                    event_id_prefix=event_id_prefix,
                    skip_events=skip_events,
                )
            )
        except BaseException as exc:  # pragma: no cover - defensive bridge
            queue.put(("error", exc))
        finally:
            queue.put(("done", None))

    thread = Thread(target=producer, daemon=True)
    thread.start()
    try:
        while True:
            kind, payload = queue.get()
            if kind == "done":
                break
            if kind == "error":
                assert isinstance(payload, BaseException)
                raise payload
            yield payload
    finally:
        thread.join(timeout=0.1)


async def _produce_action_sse(
    items: AsyncIterable[ActionItem],
    queue: Queue[tuple[str, str | BaseException | None]],
    *,
    event_id_prefix: str = "",
    skip_events: int = 0,
) -> None:
    redirect_seen = False
    event_index = 0
    async_iterator = items.__aiter__()
    while True:
        item = await _next_async_action_item(async_iterator)
        if item is _ITERATION_DONE:
            break
        event_index += 1
        event_name, payload = serialize_action_item(item)
        if event_index > skip_events:
            queue.put(
                (
                    "event",
                    _format_sse_event(
                        event_name,
                        payload,
                        _event_id(event_id_prefix, event_index),
                    ),
                )
            )
        if isinstance(item, Redirect):
            redirect_seen = True
            break

    if not redirect_seen:
        event_index += 1
        if event_index > skip_events:
            queue.put(
                (
                    "event",
                    _format_sse_event(
                        "end", {}, _event_id(event_id_prefix, event_index)
                    ),
                )
            )


async def stream_action_exception_sse_async(
    status: int,
    message: str,
    *,
    event_id_prefix: str = "",
    skip_events: int = 0,
) -> AsyncIterator[str]:
    for chunk in stream_action_exception_sse_sync(
        status,
        message,
        event_id_prefix=event_id_prefix,
        skip_events=skip_events,
    ):
        yield chunk


def stream_action_exception_sse_sync(
    status: int,
    message: str,
    *,
    event_id_prefix: str = "",
    skip_events: int = 0,
) -> Iterator[str]:
    events = [(_action_error_event(status, message)), ("end", {})]
    for event_index, (event_name, payload) in enumerate(events, start=1):
        if event_index > skip_events:
            yield _format_sse_event(
                event_name, payload, _event_id(event_id_prefix, event_index)
            )


def serialize_action_item(item: ActionItem) -> tuple[str, dict[str, Any]]:
    if isinstance(item, Signal):
        return "patch_signals", {item.name: item.value}
    if isinstance(item, Signals):
        return "patch_signals", item.values
    if isinstance(item, HTML):
        payload: dict[str, Any] = {
            "content": item.content,
            "swap": item.swap,
        }
        if item.target:
            payload["target"] = item.target
        if item.transition:
            payload["transition"] = item.transition
        if item.focus:
            payload["focus"] = item.focus
        if item.swap_delay is not None:
            payload["swap_delay"] = item.swap_delay
        if item.settle_delay is not None:
            payload["settle_delay"] = item.settle_delay
        if item.strict_targets is not None:
            payload["strict_targets"] = item.strict_targets
        return "patch_html", payload
    if isinstance(item, Toast):
        return "toast", item.payload if isinstance(item.payload, dict) else {
            "value": item.payload
        }
    if isinstance(item, Event):
        payload: dict[str, Any] = {"name": item.name, "payload": item.payload}
        if item.target:
            payload["target"] = item.target
        return "dispatch_event", payload
    if isinstance(item, Delete):
        return "patch_html", {
            "target": item.target,
            "content": "",
            "swap": "delete",
        }
    if isinstance(item, Redirect):
        return "redirect", {"url": item.url}
    if isinstance(item, History):
        payload: dict[str, Any] = {}
        if item.push_url:
            payload["push_url"] = item.push_url
        if item.replace_url:
            payload["replace_url"] = item.replace_url
        return "history", payload
    if isinstance(item, LoadJS):
        return "load_js", {"src": item.src}
    raise TypeError(f"Unsupported action item type: {type(item).__name__}")


def _format_sse_event(
    event_name: str, payload: dict[str, Any], event_id: str = ""
) -> str:
    body = json.dumps(payload)
    id_line = f"id: {event_id}\n" if event_id else ""
    return f"event: {event_name}\n{id_line}data: {body}\n\n"


def _event_id(prefix: str, event_index: int) -> str:
    return f"{prefix}:{event_index}" if prefix else ""


def _sse_resume_context(request: HttpRequest | None) -> tuple[str, int]:
    if request is None:
        return "", 0

    request_id = request.headers.get("X-Hyper-Request-ID", "").strip()
    if not _VALID_SSE_REQUEST_ID.fullmatch(request_id):
        return "", 0

    last_event_id = request.headers.get("Last-Event-ID", "").strip()
    prefix, separator, raw_index = last_event_id.rpartition(":")
    if separator and prefix == request_id and raw_index.isdigit():
        return request_id, int(raw_index)
    return request_id, 0


def _is_asgi_request(request: HttpRequest | None) -> bool:
    return bool(request is not None and hasattr(request, "scope"))


def _next_action_item(iterator: Iterator[ActionItem]) -> ActionItem | object:
    return next(iterator, _ITERATION_DONE)


async def _next_async_action_item(
    iterator: AsyncIterator[ActionItem],
) -> ActionItem | object:
    try:
        return await iterator.__anext__()
    except StopAsyncIteration:
        return _ITERATION_DONE
