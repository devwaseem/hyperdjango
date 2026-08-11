from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.test import override_settings


def test_devtools_full_middleware_and_streaming_integration() -> None:
    script = r"""
from django.conf import settings

settings.configure(
    DEBUG=True,
    SECRET_KEY="test",
    DEFAULT_CHARSET="utf-8",
    ALLOWED_HOSTS=["testserver"],
    ROOT_URLCONF=__name__,
    STATIC_URL="/static/",
    HYPER_DEBUG_TOOLBAR=True,
    HYPER_DEBUG_TOOLBAR_CONFIG={"MAX_HISTORY": 10},
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    INSTALLED_APPS=[
        "django.contrib.staticfiles",
        "hyperdjango",
        "hyperdjango.integrations.devtools",
    ],
    MIDDLEWARE=[
        "hyperdjango.integrations.devtools.middleware.HyperDjangoDebugToolbarMiddleware",
    ],
    TEMPLATES=[{
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
    }],
)

import django
django.setup()

import json
import logging
from django.db import connection
from django.http import HttpResponse
from django.test import AsyncRequestFactory, Client
from django.urls import include, path
from hyperdjango.actions import Event, HTML, action
from hyperdjango.integrations.devtools.middleware import HyperDjangoDebugToolbarMiddleware
from hyperdjango.page import HyperView
from hyperdjango.runtime.dispatcher import dispatch_page, dispatch_page_async

class DemoPage(HyperView):
    @classmethod
    def resolve_import(cls, *, file_name):
        return iter(())

    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        logging.getLogger("demo.trace").warning("page rendered")
        return HttpResponse("<html><body><h1>Demo</h1></body></html>")

    @action
    def stream(self, request, **kwargs):
        yield Event(name="phase", payload={"step": 1, "token": "secret"})
        yield HTML(content="<p>done</p>", target="#result", swap="inner")

    @action
    def immediate(self, request, **kwargs):
        return HTML(content="<p>immediate</p>", target="#result", swap="inner")

def demo(request):
    return dispatch_page(DemoPage(), request)

urlpatterns = [
    path("__hyperdebug__/", include("hyperdjango.integrations.devtools.urls")),
    path("", demo, name="hyper_home"),
]

client = Client()
request_headers = {f"X-Debug-{index}": f"value-{index}" for index in range(15)}
request_headers["Authorization"] = "Bearer hidden"
page = client.get("/", headers=request_headers)
assert page.status_code == 200
assert page.headers["X-HyperDjango-Debug-ID"]
assert b"hyperdjango/dev-toolbar.js" in page.content
assert b'/static/hyperdjango/dev-toolbar.js?v=' in page.content
assert b'data-styles-url="/static/hyperdjango/dev-toolbar.css?v=' in page.content

page_id = page.headers["X-HyperDjango-Debug-ID"]
page_trace = client.get(f"/__hyperdebug__/requests/{page_id}/").json()["record"]
assert page_trace["route"]["handler"] == "get"
assert page_trace["request"]["path"] == "/"
assert all(
    page_trace["request"]["headers"][f"X-Debug-{index}"] == f"value-{index}"
    for index in range(15)
)
assert page_trace["request"]["headers"]["Authorization"] == "[redacted]"
assert "…" not in page_trace["request"]["headers"]
assert len(page_trace["sql"]) == 1
assert page_trace["sql"][0]["duration_ms"] >= 0
assert page_trace["logs"][0]["logger"] == "demo.trace"
assert page_trace["costs"]["sql_queries"] == 1
assert page_trace["costs"]["response_bytes"] > 0
assert any(event["kind"] == "route resolved" for event in page_trace["lifecycle"])

stream = client.post(
    "/",
    HTTP_X_HYPER_ACTION="stream",
    HTTP_X_HYPER_DATA='{"password":"hidden","visible":7}',
)
stream_id = stream.headers["X-HyperDjango-Debug-ID"]
before = client.get(f"/__hyperdebug__/requests/{stream_id}/").json()["record"]
assert before["results"][0]["iteration_status"] == "not started"

stream_iterator = iter(stream.streaming_content)
first_chunk = next(stream_iterator)
during = client.get(f"/__hyperdebug__/requests/{stream_id}/").json()["record"]
during_result = during["results"][0]
assert during_result["iteration_status"] == "streaming"
assert during_result["item_types"] == ["Event"]
assert during_result["items"][0]["payload"]["token"] == "[redacted]"

chunks = [first_chunk, *stream_iterator]
assert chunks[-1].startswith(b"event: end")
after = client.get(f"/__hyperdebug__/requests/{stream_id}/").json()["record"]
result = after["results"][0]
assert result["iteration_status"] == "completed"
assert result["item_types"] == ["Event", "HTML"]
assert result["items"][0]["payload"]["token"] == "[redacted]"
assert result["items"][1]["target"] == "#result"
assert result["items"][1]["content"] == "<p>done</p>"
assert result["items"][0]["sequence"] == 1
assert result["items"][0]["event"] == "dispatch_event"
assert result["items"][0]["delivered"] is True
assert result["items"][0]["payload_bytes"] > 0
assert result["items"][1]["gap_ms"] >= 0
assert after["action"]["arguments"]["password"] == "[redacted]"
assert "stream iteration" in {timing["phase"] for timing in after["timings"]}
assert all("start_ms" in timing for timing in after["timings"])
assert all("end_ms" in timing for timing in after["timings"])
assert all("depth" in timing for timing in after["timings"])
action_timing = next(timing for timing in after["timings"] if timing["phase"] == "action")
dispatch_timing = next(timing for timing in after["timings"] if timing["phase"] == "dispatch")
assert action_timing["parent"] == "dispatch"
assert action_timing["depth"] > dispatch_timing["depth"]
assert after["response"]["request_duration_ms"] >= before["response"]["request_duration_ms"]
assert after["response"]["response_ready_ms"] <= after["response"]["request_duration_ms"]

history = client.get("/__hyperdebug__/history/").json()["records"]
assert history[0]["id"] == stream_id
assert history[0]["stream_status"] == "completed"
assert not any(record["path"].startswith("/__hyperdebug__/") for record in history)

resumed = client.post(
    "/",
    HTTP_X_HYPER_ACTION="stream",
    HTTP_X_HYPER_REQUEST_ID="resume-1",
    HTTP_LAST_EVENT_ID="resume-1:1",
)
resumed_id = resumed.headers["X-HyperDjango-Debug-ID"]
list(resumed.streaming_content)
resumed_result = client.get(f"/__hyperdebug__/requests/{resumed_id}/").json()["record"]["results"][0]
assert resumed_result["resume_from"] == "resume-1:1"
assert resumed_result["items"][0]["event_id"] == "resume-1:1"
assert resumed_result["items"][0]["delivered"] is False
assert resumed_result["items"][1]["delivered"] is True

cancelled = client.post("/", HTTP_X_HYPER_ACTION="stream")
cancelled_id = cancelled.headers["X-HyperDjango-Debug-ID"]
cancelled_iterator = iter(cancelled.streaming_content)
next(cancelled_iterator)
cancelled.close()
cancelled_trace = client.get(f"/__hyperdebug__/requests/{cancelled_id}/").json()["record"]
assert cancelled_trace["response"]["stream_status"] == "closed"
assert cancelled_trace["results"][0]["iteration_status"] == "closed"

immediate = client.post("/", HTTP_X_HYPER_ACTION="immediate")
immediate_id = immediate.headers["X-HyperDjango-Debug-ID"]
initial_history = client.get("/__hyperdebug__/history/").json()["records"]
assert initial_history[0]["id"] == immediate_id
assert initial_history[0]["stream_status"] is None
list(immediate.streaming_content)
completed_history = client.get("/__hyperdebug__/history/").json()["records"]
assert completed_history[0]["id"] == immediate_id
assert completed_history[0]["stream_status"] == "completed"

long_class = "class-" + ("x" * 240)
client_update = client.post(
    f"/__hyperdebug__/requests/{immediate_id}/client/",
    data=json.dumps({
        "events": [{
            "kind": "DOM swap",
            "target": "#result",
            "added_total": 1,
            "removed_total": 0,
            "changed_total": 1,
            "added_nodes": ["button:nth-child(1) · button#save"],
            "changed_nodes": [
                f':scope · input#demo: attribute class: "before" → "{long_class}"'
            ],
        }],
        "summary": {f"summary_key_{index}": index for index in range(15)} | {
            "swaps": 1,
            "nodes_added": 1,
            "nodes_changed": 1,
        },
    }),
    content_type="application/json",
)
assert client_update.status_code == 200
client_trace = client.get(f"/__hyperdebug__/requests/{immediate_id}/").json()["record"]
assert client_trace["client"]["events"][0]["kind"] == "DOM swap"
assert client_trace["client"]["events"][0]["added_nodes"] == [
    "button:nth-child(1) · button#save"
]
assert "before" in client_trace["client"]["events"][0]["changed_nodes"][0]
assert long_class in client_trace["client"]["events"][0]["changed_nodes"][0]
assert "…" not in client_trace["client"]["events"][0]["changed_nodes"][0]
assert client_trace["client"]["summary"]["swaps"] == 1
assert all(
    client_trace["client"]["summary"][f"summary_key_{index}"] == index
    for index in range(15)
)
assert "…" not in client_trace["client"]["summary"]

assert client.post(f"/__hyperdebug__/requests/{immediate_id}/pin/").json()["pinned"] is True
assert client.post("/__hyperdebug__/controls/clear/").json()["cleared"] >= 1
assert client.get(f"/__hyperdebug__/requests/{immediate_id}/").status_code == 200
assert client.post("/__hyperdebug__/controls/pause/").json()["paused"] is True
assert client.get("/__hyperdebug__/history/").json()["paused"] is True
paused_count = len(client.get("/__hyperdebug__/history/").json()["records"])
paused_page = client.get("/")
assert b"hyperdjango/dev-toolbar.js" in paused_page.content
assert "X-HyperDjango-Debug-ID" not in paused_page.headers
assert len(client.get("/__hyperdebug__/history/").json()["records"]) == paused_count
assert client.post("/__hyperdebug__/controls/pause/").json()["paused"] is False

class AsyncPage(HyperView):
    @classmethod
    def resolve_import(cls, *, file_name):
        return iter(())

    async def get(self, request):
        return HttpResponse("<html><body>async</body></html>")

async def async_response(request):
    return await dispatch_page_async(AsyncPage(), request)

async def run_async_request():
    request = AsyncRequestFactory().get("/async", HTTP_HOST="testserver")
    response = await HyperDjangoDebugToolbarMiddleware(async_response)(request)
    assert response.status_code == 200
    assert response.headers["X-HyperDjango-Debug-ID"]
    assert b"hyperdjango/dev-toolbar.js" in response.content

import asyncio
asyncio.run(run_async_request())
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_devtools_checks_warn_only_when_enabled() -> None:
    if not settings.configured:
        settings.configure(DEBUG=False, MIDDLEWARE=[])

    from hyperdjango.integrations.devtools.checks import (
        check_devtools_configuration,
    )

    with override_settings(
        HYPER_DEBUG_TOOLBAR=False,
        DEBUG=False,
        MIDDLEWARE=[],
    ):
        assert check_devtools_configuration(None) == []

    with override_settings(
        HYPER_DEBUG_TOOLBAR=True,
        DEBUG=False,
        MIDDLEWARE=[],
    ):
        messages = check_devtools_configuration(None)
    assert [message.id for message in messages] == [
        "hyperdjango_devtools.W002",
        "hyperdjango_devtools.W003",
    ]


def test_devtools_assets_expose_rich_brutalist_inspector() -> None:
    root = Path(__file__).resolve().parent.parent
    runtime = (root / "hyperdjango/static/hyperdjango/dev-toolbar.js").read_text()
    styles = (root / "hyperdjango/static/hyperdjango/dev-toolbar.css").read_text()
    fonts = root / "hyperdjango/static/hyperdjango/fonts"

    tab_block = runtime[
        runtime.index("const tabs = [") : runtime.index("const legacyTabs")
    ]
    overview_block = runtime[
        runtime.index("function renderOverview(record)") : runtime.index(
            "function observedAssetState"
        )
    ]
    for label in (
        "Overview",
        "Route",
        "Action",
        "Output",
        "Timeline",
        "Database",
        "Request / Response",
        "Errors / Logs",
    ):
        assert label in tab_block
    assert tab_block.count('["') == 8
    for removed_id in (
        "flow",
        "dom",
        "diagnostics",
        "client",
        "lifecycle",
        "logs",
        "renders",
        "results",
    ):
        assert f'["{removed_id}",' not in tab_block
    assert "renderOverviewDiagnostics(record)" in runtime
    assert "Route resolution" not in overview_block
    assert "Action dispatch" not in overview_block
    assert "renderOutputWorkspace" in runtime
    assert "renderTimelineWorkspace" in runtime
    output_workspace = runtime[
        runtime.index("function renderOutputWorkspace") : runtime.index(
            "function renderClient"
        )
    ]
    timeline_workspace = runtime[
        runtime.index("function renderTimelineWorkspace") : runtime.index(
            "function renderLogs"
        )
    ]
    assert "renderRenders(record)" in output_workspace
    assert "renderSseWaterfall" not in output_workspace
    assert "renderSseWaterfall(record.results || [])" in timeline_workspace
    assert 'renders: "output"' in runtime
    assert 'results: "output"' in runtime
    assert "database: renderDatabase" in runtime
    assert "renderProblems" in runtime
    assert 'window.addEventListener("hyper:afterRequest"' in runtime
    assert 'headers?.get("X-HyperDjango-Debug-ID")' in runtime
    assert "REPLAY ACTION" in runtime
    assert "PIN TRACE" not in runtime
    assert 'data-action="pin" data-slot="pin"' not in runtime
    assert 'data-action="pin-request" data-pin-request-id=' in runtime
    assert 'class="hdd-history-entry' in runtime
    assert "record.pinned = !previous" in runtime
    assert "HyperDjango trace pin failed" in runtime
    trace_actions = runtime[
        runtime.index("function traceActions(record)") : runtime.index(
            "function updatePanel"
        )
    ]
    assert 'data-action="pin"' not in trace_actions
    assert "EXPORT JSON" not in runtime
    assert "Raw trace" not in runtime
    assert "renderRaw" not in runtime
    assert "hdd-json" not in styles
    assert 'data-action="pause"' in runtime
    assert 'data-action="clear"' in runtime
    assert 'data-action="fullscreen"' in runtime
    assert 'data-slot="launcher-grip"' in runtime
    assert 'data-slot="launcher-count"' in runtime
    assert 'class="hdd-launcher-mark"' not in runtime
    assert 'slots["launcher-count"].textContent = state.history.length' in runtime
    assert 'localStorage.setItem("hyperdjango.debug.launcherX"' in runtime
    assert 'launcherGrip.addEventListener("pointermove"' in runtime
    assert "translate3d(var(--hdd-launcher-x" in styles
    assert 'root.classList.toggle("is-fullscreen", state.fullscreen)' in runtime
    assert 'role="tablist"' in runtime
    assert 'role="tabpanel"' in runtime
    assert 'aria-label="Selected trace details"' in runtime
    assert 'aria-labelledby", `hdd-tab-${state.activeTab}`' in runtime
    assert 'role="tab"' in runtime
    assert 'aria-selected="${active}"' in runtime
    assert 'slots.tabs.addEventListener("keydown"' in runtime
    assert "setToolbarOpen(false, { instant: true })" not in runtime
    assert "transition: transform 240ms var(--hdd-ease-out)" in styles
    assert "closeDuration" in runtime
    assert "state.tabsMarkup !== markup" in runtime
    assert "state.panelMarkup === markup" in runtime
    assert "preservePanelState: background" in runtime
    assert "updateTabOverflow" in runtime
    assert 'data-action="tab-prev"' in runtime
    assert 'data-action="tab-next"' in runtime
    assert 'data-slot="tab-select"' in runtime
    assert 'slots["tab-select"].value = state.activeTab' in runtime
    assert "activateTab(event.target.value, { focus: false })" in runtime
    assert ".hdd-tab-picker" in styles
    assert ".hdd-tabbar.has-overflow .hdd-tab-scroll," in styles
    assert 'window.addEventListener("hyper:swap:start"' in runtime
    assert 'window.addEventListener("hyper:swap:end"' in runtime
    assert 'window.addEventListener("hyper:streamEvent"' in runtime
    assert 'window.addEventListener("hyper:requestRetry"' not in runtime
    assert '"hyper:requestRetry": "stream retry"' in runtime
    assert "diffSnapshots" in runtime
    assert "parseDiffItem" in runtime
    assert "Attributes changed" in runtime
    assert "Text changed" in runtime
    assert 'data-action="highlight-dom"' in runtime
    assert 'label = "Locate DOM element"' in runtime
    assert 'aria-label="${esc(label)}"' in runtime
    assert '<svg viewBox="0 0 16 16" aria-hidden="true">' in runtime
    assert ".hdd-dom-reference button svg" in styles
    assert "highlightDomElement" in runtime
    assert "scrollIntoView" in runtime
    assert "data-hyperdjango-dom-highlight" in runtime
    assert "0 0 0 9999px rgba(0, 0, 0, 0.58)" in runtime
    assert 'background: "transparent"' in runtime
    assert ".hdd-dom-reference" in styles
    assert "observeRequestMutations" in runtime
    assert "observed_fallback: true" in runtime
    assert "TARGET_NO_OUTCOME" in runtime
    assert "TERMINAL_EVENT_MISSING" in runtime
    assert "vscode://file" in runtime
    assert "source.display_file || source.file" in runtime
    assert "renderRoute" in runtime
    assert "CURRENT DOCUMENT OBSERVATION" in runtime
    assert "observedAssetState" in runtime
    assert "Selected request dispatch" in runtime
    assert "ROUTE INVENTORY" not in runtime
    assert "SSE item waterfall" in runtime
    assert "N+1 GROUPS" in runtime
    assert "HYPERDJANGO SQL CONTEXT" in runtime
    assert "hdd-query-disclosure" in runtime
    assert "SANITIZED PARAMETERS" in runtime
    assert "Request-scoped server logs" in runtime
    assert "Request journey" in runtime
    assert "lifecycleMilestones" in runtime
    assert "LOW-LEVEL EVENTS SUMMARIZED" in runtime
    assert "Server and browser clocks" in runtime
    assert "Traceback frames" in runtime
    assert 'attachShadow({ mode: "open" })' in runtime
    assert 'new URL("dev-toolbar.css", script.src).href' in runtime
    assert 'setProperty("visibility", "hidden", "important")' in runtime
    assert 'setProperty("visibility", "visible", "important")' in runtime
    assert "streamIsPending" in runtime
    assert "record?.response?.streaming" in runtime
    assert "background: true" in runtime
    assert '"Content", "Metadata"' in runtime
    assert 'window.addEventListener("hyper:actionSwitch"' in runtime
    assert "parent_request_id" in runtime
    assert "switch_depth" in runtime
    assert "hdd-content-preview" in runtime
    assert "Execution waterfall" in runtime
    assert "django request pipeline" in runtime
    assert "django response pipeline" in runtime
    assert "stream handoff" in runtime
    assert "stream pending" in runtime
    assert "time containment" in runtime
    assert "response_ready_ms" in runtime
    assert "DIRECTLY INSTRUMENTED" in runtime
    assert "hdd-parent-interval" in runtime
    assert "--hdd-left" in runtime
    assert 'slots.tabs.addEventListener("wheel"' in runtime
    assert "const tabStart = activeTab.offsetLeft" in runtime
    assert "slots.tabs.scrollLeft = tabStart" in runtime
    assert "slots.tabs.scrollLeft = tabEnd - slots.tabs.clientWidth" in runtime
    assert "focus({ preventScroll: true })" in runtime
    assert ":host" in styles
    assert "all: initial" in styles
    assert 'font-family: "HyperDjango Doto"' in styles
    assert 'font-family: "HyperDjango IBM Plex Mono"' in styles
    assert (fonts / "doto-800-latin.woff2").is_file()
    assert (fonts / "ibm-plex-mono-400-latin.woff2").is_file()
    assert (fonts / "ibm-plex-mono-700-latin.woff2").is_file()
    assert (fonts / "LICENSE-Doto.txt").is_file()
    assert (fonts / "LICENSE-IBM-Plex-Mono.txt").is_file()
    assert "prefers-reduced-motion" in styles
    assert ".hdd-search:focus-within" in styles
    assert "@media (pointer: coarse)" in styles
    assert "@media (prefers-color-scheme: dark)" not in styles
    assert "color-scheme: light" in styles
    assert ".hdd-tabbar.has-overflow" in styles
    assert "--hdd-header-bg" in styles
    assert "--hdd-row-hover" in styles
    assert "REQUEST INSPECTOR / DEV ONLY" not in runtime
    assert 'class="hdd-brand"' in runtime
    assert "REQUEST INSPECTOR" in runtime
    assert 'class="hdd-brand"><span>' not in runtime
    assert "<small>ROUTE</small>" in runtime
    assert "<small>ACTION</small>" in runtime
    assert ".hdd-route-title > small" in styles
    assert "min-width: 44px; min-height: 44px" in styles
    assert "hdd-pulse" not in styles
    assert "border-radius: 0" in styles
    assert "width: 100vw" in styles
    assert "height: 50dvh" in styles
    assert "height: 100dvh" in styles
    assert "height: 78dvh" in styles
    assert "height: 85dvh" in styles
    assert "transform: translateY(100%)" in styles
    assert "--hdd-content-gutter: clamp(16px, 1.5vw, 24px)" in styles
    assert "--hdd-space-4: 16px" in styles
    assert ":where(" in styles
    assert "padding: var(--hdd-content-gutter)" in styles
    assert ".hdd-tabs::-webkit-scrollbar { display: none;" in styles
    assert "scrollbar-width: none" in styles
    assert "color: var(--hdd-paper) !important" in styles
    assert ".hdd-content-preview" in styles
    assert ".hdd-query-disclosure" in styles
    assert "#hd-debug-toolbar .hdd-tabs button span" in styles
    assert "margin-left: var(--hdd-space-2)" in styles
    assert "padding: 0 var(--hdd-space-6) 0 var(--hdd-space-3)" in styles
    assert ".hdd-waterfall-scale" in styles
    assert ".hdd-waterfall" in styles
    assert ".hdd-waterfall-legend" in styles
    assert ".hdd-parent-interval" in styles
    assert "text-overflow: ellipsis" in styles
    assert '<small title="${esc(relation)}">' in runtime
    assert ".hdd-diff-grid" in styles
    assert "grid-template-columns: minmax(0, 1fr)" in styles
    assert ".hdd-diff-group { min-width: 0; overflow: hidden;" in styles
    assert ".hdd-diff-item" in styles
    assert ".hdd-diff-value" in styles
    assert ".hdd-diff-value { grid-column: 1 / -1; overflow: auto;" in styles
    assert ".hdd-diff-locate { grid-column: 2; grid-row: 1;" in styles
    assert "function domLocateButton" in runtime
    assert "function copyButton" in runtime
    assert "async function copyToClipboard" in runtime
    assert 'data-action="copy"' in runtime
    assert "Copy DOM selector" in runtime
    assert "Copy request path" in runtime
    assert "Copy source location" in runtime
    assert "Copy result content" in runtime
    assert "Copy SQL" in runtime
    assert ".hdd-copy-button" in styles
    assert ".hdd-copy-block" in styles
    assert ".hdd-copy-label" in styles
    assert "navigator.clipboard?.writeText" in runtime
    assert 'document.execCommand("copy")' in runtime
    assert "function uniqueElementSelector" in runtime
    assert "document.querySelectorAll(selector).length === 1" in runtime
    assert "trigger_element_selector: uniqueElementSelector(detail.sourceEl)" in runtime
    assert "target_selector: after.selector" in runtime
    assert "matches.length !== 1" in runtime
    assert "DOM elements match; exact element unavailable" in runtime
    assert '!key.endsWith("_selector")' in runtime
    assert ".hdd-diagnostic" in styles
    assert ".hdd-health-strip" in styles
    assert "REQUEST HEALTH" in runtime
    assert "PASSED</small>" not in runtime
    assert ".hdd-journey" in styles
    assert ".hdd-journey-note" in styles
    assert ".hdd-source-link" in styles
    assert ".hdd-source-ref" in styles
    assert 'class="hdd-source-ref"' in runtime
    assert ".hdd-route-identity" in styles
    assert ".hdd-title-block { width: 100%; max-width: none;" in styles
    assert ".hdd-health-strip { min-width: 0; flex-direction: column;" in styles
    assert ".hdd-metric { flex: 0 0 132px;" in styles
    assert ".hdd-title-block { max-width: 1000px;" not in styles
    assert "white-space: nowrap" in styles
    assert "white-space: pre;" in styles
    assert "overflow-wrap: anywhere" not in styles
    assert "box-shadow" not in styles
    assert "DEBUG TAPE" not in runtime
    assert "linear-gradient" not in styles

    package_config = (root / "pyproject.toml").read_text()
    assert '"static/**/*.css"' in package_config
    assert '"static/**/*.woff2"' in package_config
