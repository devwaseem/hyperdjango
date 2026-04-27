from __future__ import annotations

import json
from collections.abc import AsyncIterable, AsyncIterator, Iterable, Iterator
from typing import Any

from asgiref.sync import async_to_sync, sync_to_async
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


ACTION_VARY_HEADERS = [
    "X-Hyper-Action",
    "X-Hyper-Target",
    "X-Hyper-Data",
    "X-Requested-With",
]

_ITERATION_DONE = object()


def ensure_action_response_headers(response: HttpResponse) -> HttpResponse:
    patch_vary_headers(response, ACTION_VARY_HEADERS)
    response["Cache-Control"] = "no-store, no-cache, max-age=0, must-revalidate"
    response["Pragma"] = "no-cache"
    return response


def to_action_http_response(
    result: Any, *, request: HttpRequest | None = None
) -> HttpResponse:
    items, status, headers = normalize_action_result(result)
    streaming_content: Iterable[str] | AsyncIterator[str]
    if _is_asgi_request(request):
        streaming_content = stream_action_sse_async(items)
    else:
        streaming_content = stream_action_sse_sync(items)
    response = StreamingHttpResponse(
        streaming_content,
        status=status,
        content_type="text/event-stream",
    )
    response["X-Accel-Buffering"] = "no"
    for key, value in headers.items():
        response[key] = value
    return ensure_action_response_headers(response)


def _action_error_event(status: int, message: str) -> tuple[str, dict[str, Any]]:
    return "error", {"status": status, "message": message}


def to_action_exception_response(
    status: int, message: str, *, request: HttpRequest | None = None
) -> HttpResponse:
    response = StreamingHttpResponse(
        stream_action_exception_sse_async(status, message)
        if _is_asgi_request(request)
        else [
            _format_sse_event(*_action_error_event(status, message)),
            _format_sse_event("end", {}),
        ],
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
        items.append(Redirect(url=result.redirect_to, replace=bool(result.replace_url)))
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


def stream_action_sse(items: Iterable[ActionItem]) -> Iterator[str]:
    redirect_seen = False
    for item in items:
        event_name, payload = serialize_action_item(item)
        yield _format_sse_event(event_name, payload)
        if isinstance(item, Redirect):
            redirect_seen = True
            break
    if not redirect_seen:
        yield _format_sse_event("end", {})


def stream_action_sse_sync(
    items: Iterable[ActionItem] | AsyncIterable[ActionItem],
) -> Iterator[str]:
    if isinstance(items, AsyncIterable):
        return _stream_action_sse_sync_from_async(items)
    return stream_action_sse(items)


async def stream_action_sse_async(
    items: Iterable[ActionItem] | AsyncIterable[ActionItem],
) -> AsyncIterator[str]:
    redirect_seen = False
    if isinstance(items, AsyncIterable):
        async_iterator = items.__aiter__()
        while True:
            item = await _next_async_action_item(async_iterator)
            if item is _ITERATION_DONE:
                break
            event_name, payload = serialize_action_item(item)
            yield _format_sse_event(event_name, payload)
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
            event_name, payload = serialize_action_item(item)
            yield _format_sse_event(event_name, payload)
            if isinstance(item, Redirect):
                redirect_seen = True
                break

    if not redirect_seen:
        yield _format_sse_event("end", {})


def _stream_action_sse_sync_from_async(
    items: AsyncIterable[ActionItem],
) -> Iterator[str]:
    redirect_seen = False
    async_iterator = items.__aiter__()
    while True:
        item = async_to_sync(_next_async_action_item)(async_iterator)
        if item is _ITERATION_DONE:
            break
        event_name, payload = serialize_action_item(item)
        yield _format_sse_event(event_name, payload)
        if isinstance(item, Redirect):
            redirect_seen = True
            break

    if not redirect_seen:
        yield _format_sse_event("end", {})


async def stream_action_exception_sse_async(
    status: int, message: str
) -> AsyncIterator[str]:
    yield _format_sse_event(*_action_error_event(status, message))
    yield _format_sse_event("end", {})


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
        return "redirect", {"url": item.url, "replace": item.replace}
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


def _format_sse_event(event_name: str, payload: dict[str, Any]) -> str:
    body = json.dumps(payload)
    return f"event: {event_name}\ndata: {body}\n\n"


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
