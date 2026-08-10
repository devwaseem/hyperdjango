from __future__ import annotations

from inspect import isawaitable

from debug_toolbar.panels import Panel

from hyperdjango.integrations.debug_toolbar.tracing import (
    RequestTrace,
    clear_trace,
    record_exception,
    record_response,
    start_trace,
)


class HyperDjangoPanel(Panel):
    """Request-local route, action, render, result, and timing diagnostics."""

    is_async = True
    title = "HyperDjango"
    template = "hyperdjango/debug_toolbar/panel.html"

    def __init__(self, toolbar, get_response):
        super().__init__(toolbar, get_response)
        self._trace: RequestTrace | None = None

    @property
    def nav_subtitle(self) -> str:
        stats = self.get_stats()
        if not stats.get("is_hyperdjango"):
            return "No dispatch"
        action = stats.get("action", {}).get("name")
        total = stats.get("total_ms", 0)
        label = f"Action {action}" if action else stats.get("route", {}).get("handler")
        return f"{label or 'request'} · {total:.1f} ms"

    def process_request(self, request):
        trace = start_trace(request)
        self._trace = trace
        try:
            response = self.get_response(request)
        except BaseException as exc:
            record_exception(request, exc, phase="request")
            clear_trace(request, trace)
            raise

        if isawaitable(response):
            return self._finish_async(request, trace, response)

        record_response(request, response)
        clear_trace(request, trace)
        return response

    async def _finish_async(self, request, trace, response_awaitable):
        try:
            response = await response_awaitable
            record_response(request, response)
            return response
        except BaseException as exc:
            record_exception(request, exc, phase="request")
            raise
        finally:
            clear_trace(request, trace)

    def generate_stats(self, request, response) -> None:
        trace = self._trace
        if trace is None:
            trace = RequestTrace(
                request={"method": str(request.method), "path": str(request.path)}
            )
        record_response(request, response)
        stats = trace.snapshot()
        self.record_stats(stats)

    def generate_server_timing(self, request, response) -> None:
        if self._trace is None:
            return
        total = self._trace.snapshot()["total_ms"]
        if total:
            self.record_server_timing("dispatch", "HyperDjango dispatch", total)
