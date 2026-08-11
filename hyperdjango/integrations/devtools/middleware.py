from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from html import escape
from inspect import iscoroutinefunction
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from asgiref.sync import markcoroutinefunction
from django.conf import settings
from django.templatetags.static import static
from django.urls import NoReverseMatch, reverse

from hyperdjango.integrations.debug_toolbar.tracing import (
    RequestTrace,
    clear_trace,
    record_exception,
    record_response,
    record_stream_finished,
    sanitize_mapping,
    sanitize_value,
    start_trace,
)
from hyperdjango.conf import get_vite_dev_server_url, is_dev_env
from hyperdjango.integrations.devtools import is_enabled
from hyperdjango.integrations.devtools.collectors import start_collectors
from hyperdjango.integrations.devtools.request_logging import set_request_log_context
from hyperdjango.integrations.devtools.store import request_store


HEADER_NAME = "X-HyperDjango-Debug-ID"
REQUEST_ID_ATTRIBUTE = "_hyperdjango_debug_toolbar_id"
COLLECTORS_ATTRIBUTE = "_hyperdjango_debug_toolbar_collectors"
ASSET_ROOT = Path(__file__).resolve().parents[2] / "static" / "hyperdjango"


def _versioned_static(filename: str) -> str:
    url = static(f"hyperdjango/{filename}")
    try:
        version = (ASSET_ROOT / filename).stat().st_mtime_ns
    except OSError:
        version = 1
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}v={version}"


def _internal_prefix() -> str:
    config = getattr(settings, "HYPER_DEBUG_TOOLBAR_CONFIG", {})
    return "/" + str(config.get("URL_PREFIX", "__hyperdebug__")).strip("/") + "/"


def _request_details(request, request_id: str) -> dict[str, Any]:
    return {
        "id": request_id,
        "method": str(request.method),
        "path": str(request.path),
        "full_path": str(request.get_full_path()),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "scheme": str(request.scheme),
        "host": str(request.get_host()),
        "content_type": str(request.content_type or ""),
        "content_length": request.headers.get("Content-Length"),
        "query": sanitize_value({key: values for key, values in request.GET.lists()}),
        "headers": sanitize_mapping(dict(request.headers)),
    }


class HyperDjangoDebugToolbarMiddleware:
    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        self.async_mode = iscoroutinefunction(get_response)
        if self.async_mode:
            markcoroutinefunction(self)

    def __call__(self, request):
        if self.async_mode:
            return self.__acall__(request)
        if not self._should_trace(request):
            response = self.get_response(request)
            if self._should_inject_while_paused(request):
                self._inject_toolbar(request, "", response)
            return response

        trace, request_id, started = self._start(request)
        try:
            response = self.get_response(request)
        except BaseException as exc:
            self._record_failure(request, trace, request_id, started, exc)
            raise
        return self._prepare_response(request, trace, request_id, started, response)

    async def __acall__(self, request):
        if not self._should_trace(request):
            response = await self.get_response(request)
            if self._should_inject_while_paused(request):
                self._inject_toolbar(request, "", response)
            return response

        trace, request_id, started = self._start(request)
        try:
            response = await self.get_response(request)
        except BaseException as exc:
            self._record_failure(request, trace, request_id, started, exc)
            raise
        return self._prepare_response(request, trace, request_id, started, response)

    @staticmethod
    def _should_trace(request) -> bool:
        return (
            is_enabled()
            and not request_store.paused
            and not request.path.startswith(_internal_prefix())
        )

    @staticmethod
    def _should_inject_while_paused(request) -> bool:
        return (
            is_enabled()
            and request_store.paused
            and not request.path.startswith(_internal_prefix())
        )

    @staticmethod
    def _start(request) -> tuple[RequestTrace, str, float]:
        request_id = uuid4().hex
        trace = start_trace(request)
        trace.request.update(_request_details(request, request_id))
        try:
            trace.costs["request_bytes"] = int(request.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            trace.costs["request_bytes"] = 0
        trace.on_update = lambda snapshot: request_store.save(request_id, snapshot)
        setattr(request, COLLECTORS_ATTRIBUTE, start_collectors(trace))
        setattr(request, REQUEST_ID_ATTRIBUTE, request_id)
        return trace, request_id, perf_counter()

    def _prepare_response(self, request, trace, request_id, started, response):
        self._record_response(request, trace, started, response)
        response[HEADER_NAME] = request_id

        if getattr(response, "streaming", False):
            request_store.save(request_id, trace.snapshot())
            self._set_request_log_context(request, request_id, trace)
            self._wrap_stream(request, trace, request_id, started, response)
            return response

        if hasattr(response, "content"):
            trace.costs["response_bytes"] = len(response.content)
        self._inject_toolbar(request, request_id, response)
        if hasattr(response, "content"):
            trace.costs["toolbar_injection_bytes"] = max(
                0, len(response.content) - trace.costs.get("response_bytes", 0)
            )
        request_store.save(request_id, trace.snapshot())
        self._set_request_log_context(request, request_id, trace)
        self._cleanup(request, trace)
        return response

    @staticmethod
    def _set_request_log_context(request, request_id: str, trace) -> None:
        try:
            trace_path = reverse("hyperdjango_devtools:detail", args=(request_id,))
            trace_url = request.build_absolute_uri(trace_path)
        except (NoReverseMatch, ValueError):
            return
        set_request_log_context(
            duration_ms=float(trace.response.get("request_duration_ms", 0)),
            trace_url=trace_url,
            action=trace.action.get("name"),
            sql_queries=int(trace.costs.get("sql_queries", 0)),
            sql_ms=float(trace.costs.get("sql_ms", 0)),
            render_ms=float(trace.costs.get("render_ms", 0)),
        )

    @staticmethod
    def _record_response(request, trace, started, response) -> None:
        record_response(request, response)
        response_ready_ms = round((perf_counter() - started) * 1000, 3)
        trace.response.update(
            {
                "request_duration_ms": response_ready_ms,
                "response_ready_ms": response_ready_ms,
                "headers": sanitize_value(dict(response.items())),
                "content_length": response.get("Content-Length"),
            }
        )
        user = getattr(request, "user", None)
        if user is not None:
            trace.request["user"] = (
                sanitize_value(user.get_username())
                if getattr(user, "is_authenticated", False)
                else "anonymous"
            )
        trace.add_lifecycle(
            "response prepared",
            status=trace.response.get("status"),
            streaming=trace.response.get("streaming"),
        )

    @staticmethod
    def _record_failure(request, trace, request_id, started, exc) -> None:
        record_exception(request, exc, phase="request")
        trace.response.update(
            {
                "status": 500,
                "request_duration_ms": round((perf_counter() - started) * 1000, 3),
                "failed": True,
            }
        )
        trace.add_lifecycle("request failed", status=500)
        HyperDjangoDebugToolbarMiddleware._cleanup(request, trace)
        request_store.save(request_id, trace.snapshot())

    def _wrap_stream(self, request, trace, request_id, started, response) -> None:
        content = response.streaming_content
        if getattr(response, "is_async", False):

            async def observe_async_stream():
                status = "completed"
                exception = None
                stream_started = perf_counter()
                try:
                    async for chunk in content:
                        self._record_stream_chunk(trace, chunk, stream_started)
                        yield chunk
                except (asyncio.CancelledError, GeneratorExit):
                    status = "closed"
                    raise
                except BaseException as exc:
                    status = "failed"
                    exception = exc
                    raise
                finally:
                    self._finalize_stream(
                        request,
                        trace,
                        request_id,
                        started,
                        stream_started,
                        status,
                        exception,
                    )

            response.streaming_content = observe_async_stream()
            return

        def observe_sync_stream():
            status = "completed"
            exception = None
            stream_started = perf_counter()
            try:
                for chunk in content:
                    self._record_stream_chunk(trace, chunk, stream_started)
                    yield chunk
            except GeneratorExit:
                status = "closed"
                raise
            except BaseException as exc:
                status = "failed"
                exception = exc
                raise
            finally:
                self._finalize_stream(
                    request,
                    trace,
                    request_id,
                    started,
                    stream_started,
                    status,
                    exception,
                )

        response.streaming_content = observe_sync_stream()

    @staticmethod
    def _finalize_stream(
        request,
        trace,
        request_id,
        started,
        stream_started,
        status,
        exception,
    ) -> None:
        record_stream_finished(request, status=status, exception=exception)
        trace.add_lifecycle(
            "response stream finished",
            status=status,
            chunks=trace.costs.get("stream_chunks", 0),
            bytes=trace.costs.get("response_bytes", 0),
        )
        trace.add_timing(
            "stream iteration", stream_started, depth=1, parent="request"
        )
        trace.response.update(
            {
                "stream_status": status,
                "request_duration_ms": round((perf_counter() - started) * 1000, 3),
            }
        )
        HyperDjangoDebugToolbarMiddleware._cleanup(request, trace)
        request_store.save(request_id, trace.snapshot())

    @staticmethod
    def _record_stream_chunk(trace, chunk, stream_started) -> None:
        if not trace.costs.get("stream_chunks"):
            trace.response["time_to_first_byte_ms"] = round(
                (perf_counter() - stream_started) * 1000, 3
            )
        size = len(chunk.encode()) if isinstance(chunk, str) else len(chunk)
        trace.costs["stream_chunks"] = trace.costs.get("stream_chunks", 0) + 1
        trace.costs["response_bytes"] = trace.costs.get("response_bytes", 0) + size

    @staticmethod
    def _cleanup(request, trace) -> None:
        collectors = getattr(request, COLLECTORS_ATTRIBUTE, None)
        if collectors is not None:
            collectors.close()
            delattr(request, COLLECTORS_ATTRIBUTE)
        clear_trace(request, trace)

    @staticmethod
    def _inject_toolbar(request, request_id: str, response) -> None:
        content_type = response.get("Content-Type", "")
        if (
            "text/html" not in content_type
            or response.get("Content-Encoding")
            or not hasattr(response, "content")
        ):
            return
        try:
            history_url = reverse("hyperdjango_devtools:history")
        except NoReverseMatch:
            return

        charset = getattr(response, "charset", "utf-8") or "utf-8"
        body = response.content.decode(charset)
        marker = body.lower().rfind("</body>")
        if marker < 0:
            return

        nonce = escape(str(getattr(request, "csp_nonce", "")), quote=True)
        nonce_attr = f' nonce="{nonce}"' if nonce else ""
        script_url = _versioned_static("dev-toolbar.js")
        styles_url = _versioned_static("dev-toolbar.css")
        vite_url = get_vite_dev_server_url() if is_dev_env() else ""
        assets = (
            f'<script src="{escape(script_url, quote=True)}" '
            f'data-record-id="{escape(request_id, quote=True)}" '
            f'data-styles-url="{escape(styles_url, quote=True)}" '
            f'data-history-url="{escape(history_url, quote=True)}" defer{nonce_attr}></script>'
        )
        if vite_url:
            assets = assets.replace(
                " defer",
                f' data-vite-url="{escape(vite_url, quote=True)}" defer',
                1,
            )
        response.content = (body[:marker] + assets + body[marker:]).encode(charset)
        response["Content-Length"] = str(len(response.content))
