from __future__ import annotations

import asyncio
import json
from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    Iterator,
)
from contextvars import copy_context
from queue import Empty, Full, Queue
from threading import Event as ThreadEvent
from threading import Thread
from typing import Any

from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.utils.cache import patch_vary_headers

from hyperdjango.actions import (
    ActionItem,
    Actions,
    ActionResult,
    Checkpoint,
    Delete,
    Event,
    HTML,
    History,
    LoadJS,
    Redirect,
    SwitchAction,
    Signal,
    Signals,
    Toast,
)
from hyperdjango.conf import get_sse_heartbeat_interval
from hyperdjango.integrations.debug_toolbar.tracing import record_stream_item
from hyperdjango.sse import (
    format_checkpoint_event_id,
    is_valid_sse_request_id,
)


ACTION_VARY_HEADERS = [
    "X-Hyper-Action",
    "X-Hyper-Target",
    "X-Hyper-Data",
    "X-Requested-With",
    "X-Hyper-Request-ID",
    "X-Hyper-Switch-Depth",
    "Last-Event-ID",
]

_ITERATION_DONE = object()
_HEARTBEAT_DUE = object()
_SSE_HEARTBEAT = ": heartbeat\n\n"


def ensure_action_response_headers(response: HttpResponse) -> HttpResponse:
    patch_vary_headers(response, ACTION_VARY_HEADERS)
    response["Cache-Control"] = "no-store, no-cache, max-age=0, must-revalidate"
    response["Pragma"] = "no-cache"
    return response


def to_action_http_response(
    result: Any, *, request: HttpRequest | None = None
) -> HttpResponse:
    items, status, headers = normalize_action_result(result)
    heartbeat_interval = (
        get_sse_heartbeat_interval()
        if isinstance(items, (Iterator, AsyncIterable))
        else 0.0
    )
    items = _observe_action_items(items, request=request)
    request_id = _sse_request_id(request)
    allow_checkpoints = _request_allows_checkpoints(request)
    streaming_content: Iterable[str] | AsyncIterator[str]
    if _is_asgi_request(request):
        streaming_content = stream_action_sse_async(
            items,
            request_id=request_id,
            allow_checkpoints=allow_checkpoints,
            heartbeat_interval=heartbeat_interval,
        )
    else:
        streaming_content = stream_action_sse_sync(
            items,
            request_id=request_id,
            allow_checkpoints=allow_checkpoints,
            heartbeat_interval=heartbeat_interval,
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
    response = StreamingHttpResponse(
        stream_action_exception_sse_async(status, message)
        if _is_asgi_request(request)
        else stream_action_exception_sse_sync(status, message),
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
            Checkpoint,
            SwitchAction,
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


def is_terminal_action_item(item: ActionItem) -> bool:
    return isinstance(item, (Redirect, SwitchAction))


def stream_action_sse(
    items: Iterable[ActionItem],
    *,
    request_id: str = "",
    allow_checkpoints: bool = False,
) -> Iterator[str]:
    terminal_seen = False
    checkpoints: set[str] = set()
    for item in items:
        yield _format_action_item(
            item,
            request_id=request_id,
            allow_checkpoints=allow_checkpoints,
            checkpoints=checkpoints,
        )
        if is_terminal_action_item(item):
            terminal_seen = True
            break
    if not terminal_seen:
        yield _format_sse_event("end", {})


def stream_action_sse_sync(
    items: Iterable[ActionItem] | AsyncIterable[ActionItem],
    *,
    request_id: str = "",
    allow_checkpoints: bool = False,
    heartbeat_interval: float = 0.0,
) -> Iterator[str]:
    if isinstance(items, AsyncIterable):
        return _stream_action_sse_sync_from_async(
            items,
            request_id=request_id,
            allow_checkpoints=allow_checkpoints,
            heartbeat_interval=heartbeat_interval,
        )
    chunks = stream_action_sse(
        items,
        request_id=request_id,
        allow_checkpoints=allow_checkpoints,
    )
    if heartbeat_interval <= 0:
        return chunks
    return _stream_sync_with_heartbeats(chunks, heartbeat_interval)


async def stream_action_sse_async(
    items: Iterable[ActionItem] | AsyncIterable[ActionItem],
    *,
    request_id: str = "",
    allow_checkpoints: bool = False,
    heartbeat_interval: float = 0.0,
) -> AsyncIterator[str]:
    terminal_seen = False
    checkpoints: set[str] = set()
    if isinstance(items, AsyncIterable):
        async_iterator = items.__aiter__()

        async def next_async_item() -> ActionItem | object:
            return await _next_async_action_item(async_iterator)

        async for item in _iterate_with_heartbeats(
            next_async_item,
            heartbeat_interval,
        ):
            if item is _HEARTBEAT_DUE:
                yield _SSE_HEARTBEAT
                continue
            if item is _ITERATION_DONE:
                break
            yield _format_action_item(
                item,
                request_id=request_id,
                allow_checkpoints=allow_checkpoints,
                checkpoints=checkpoints,
            )
            if is_terminal_action_item(item):
                terminal_seen = True
                break
    else:
        iterator = iter(items)

        async def next_sync_item() -> ActionItem | object:
            return await sync_to_async(
                _next_action_item,
                thread_sensitive=True,
            )(iterator)

        async for item in _iterate_with_heartbeats(
            next_sync_item,
            heartbeat_interval,
        ):
            if item is _HEARTBEAT_DUE:
                yield _SSE_HEARTBEAT
                continue
            if item is _ITERATION_DONE:
                break
            yield _format_action_item(
                item,
                request_id=request_id,
                allow_checkpoints=allow_checkpoints,
                checkpoints=checkpoints,
            )
            if is_terminal_action_item(item):
                terminal_seen = True
                break

    if not terminal_seen:
        yield _format_sse_event("end", {})


def _stream_action_sse_sync_from_async(
    items: AsyncIterable[ActionItem],
    *,
    request_id: str = "",
    allow_checkpoints: bool = False,
    heartbeat_interval: float = 0.0,
) -> Iterator[str]:
    queue: Queue[tuple[str, str | BaseException | None]] = Queue()

    def producer() -> None:
        try:
            asyncio.run(
                _produce_action_sse(
                    items,
                    queue,
                    request_id=request_id,
                    allow_checkpoints=allow_checkpoints,
                )
            )
        except BaseException as exc:  # pragma: no cover - defensive bridge
            queue.put(("error", exc))
        finally:
            queue.put(("done", None))

    context = copy_context()
    thread = Thread(target=context.run, args=(producer,), daemon=True)
    thread.start()
    try:
        while True:
            try:
                kind, payload = queue.get(
                    timeout=heartbeat_interval if heartbeat_interval > 0 else None
                )
            except Empty:
                yield _SSE_HEARTBEAT
                continue
            if kind == "done":
                break
            if kind == "error":
                assert isinstance(payload, BaseException)
                raise payload
            yield payload
    finally:
        thread.join(timeout=0.1)


def _stream_sync_with_heartbeats(
    chunks: Iterator[str],
    heartbeat_interval: float,
) -> Iterator[str]:
    queue: Queue[tuple[str, str | BaseException | None]] = Queue(maxsize=1)
    stopped = ThreadEvent()
    next_requested = ThreadEvent()

    def put(kind: str, payload: str | BaseException | None) -> bool:
        while not stopped.is_set():
            try:
                queue.put((kind, payload), timeout=0.1)
            except Full:
                continue
            return True
        return False

    def producer() -> None:
        try:
            while not stopped.is_set():
                next_requested.wait()
                next_requested.clear()
                if stopped.is_set():
                    return
                try:
                    chunk = next(chunks)
                except StopIteration:
                    put("done", None)
                    return
                if not put("event", chunk):
                    return
        except BaseException as exc:  # pragma: no cover - defensive bridge
            put("error", exc)

    context = copy_context()
    thread = Thread(target=context.run, args=(producer,), daemon=True)
    thread.start()
    waiting_for_next = False
    try:
        while True:
            if not waiting_for_next:
                waiting_for_next = True
                next_requested.set()
            try:
                kind, payload = queue.get(timeout=heartbeat_interval)
            except Empty:
                yield _SSE_HEARTBEAT
                continue
            waiting_for_next = False
            if kind == "done":
                break
            if kind == "error":
                assert isinstance(payload, BaseException)
                raise payload
            assert isinstance(payload, str)
            yield payload
    finally:
        stopped.set()
        next_requested.set()
        thread.join(timeout=0.1)


async def _iterate_with_heartbeats(
    next_item: Callable[[], Awaitable[ActionItem | object]],
    heartbeat_interval: float,
) -> AsyncIterator[ActionItem | object]:
    pending: asyncio.Task[ActionItem | object] | None = None
    try:
        while True:
            pending = asyncio.create_task(next_item())
            while heartbeat_interval > 0:
                done, _ = await asyncio.wait(
                    (pending,),
                    timeout=heartbeat_interval,
                )
                if done:
                    break
                yield _HEARTBEAT_DUE
            item = await pending
            pending = None
            yield item
            if item is _ITERATION_DONE:
                return
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            try:
                await pending
            except BaseException:
                pass


async def _produce_action_sse(
    items: AsyncIterable[ActionItem],
    queue: Queue[tuple[str, str | BaseException | None]],
    *,
    request_id: str = "",
    allow_checkpoints: bool = False,
) -> None:
    terminal_seen = False
    checkpoints: set[str] = set()
    async_iterator = items.__aiter__()
    while True:
        item = await _next_async_action_item(async_iterator)
        if item is _ITERATION_DONE:
            break
        queue.put(
            (
                "event",
                _format_action_item(
                    item,
                    request_id=request_id,
                    allow_checkpoints=allow_checkpoints,
                    checkpoints=checkpoints,
                ),
            )
        )
        if is_terminal_action_item(item):
            terminal_seen = True
            break

    if not terminal_seen:
        queue.put(("event", _format_sse_event("end", {})))


async def stream_action_exception_sse_async(
    status: int,
    message: str,
) -> AsyncIterator[str]:
    for chunk in stream_action_exception_sse_sync(status, message):
        yield chunk


def stream_action_exception_sse_sync(
    status: int,
    message: str,
) -> Iterator[str]:
    events = [(_action_error_event(status, message)), ("end", {})]
    for event_name, payload in events:
        yield _format_sse_event(event_name, payload)


def _format_action_item(
    item: ActionItem,
    *,
    request_id: str,
    allow_checkpoints: bool,
    checkpoints: set[str],
) -> str:
    if isinstance(item, Checkpoint):
        if not allow_checkpoints:
            raise ValueError("SSE checkpoints are only supported for GET actions")
        if not request_id:
            raise ValueError(
                "SSE checkpoints require a valid X-Hyper-Request-ID"
            )
        if item.name in checkpoints:
            raise ValueError(
                f"SSE checkpoint '{item.name}' was emitted more than once"
            )
        checkpoints.add(item.name)
        return _format_sse_checkpoint(
            format_checkpoint_event_id(request_id, item.name)
        )

    event_name, payload = serialize_action_item(item)
    return _format_sse_event(event_name, payload)


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
    if isinstance(item, Checkpoint):
        return "checkpoint", {}
    if isinstance(item, SwitchAction):
        name, data, method, url = item.resolve()
        payload: dict[str, Any] = {
            "name": name,
            "data": data,
            "method": method,
        }
        if url is not None:
            payload["url"] = url
        return "switch_action", payload
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


def _format_sse_checkpoint(event_id: str) -> str:
    return f"event: checkpoint\nid: {event_id}\n\n"


def _sse_request_id(request: HttpRequest | None) -> str:
    if request is None:
        return ""

    request_id = request.headers.get("X-Hyper-Request-ID", "").strip()
    return request_id if is_valid_sse_request_id(request_id) else ""


def _request_allows_checkpoints(request: HttpRequest | None) -> bool:
    if request is None or not isinstance(request.method, str):
        return False
    return request.method.upper() == "GET"


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
