from __future__ import annotations

import asyncio
import subprocess
import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import django
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.template import Context, Engine
from django.test import RequestFactory

from hyperdjango.actions import ActionResult, History, HTML, Redirect, action
from hyperdjango.page import HyperView
from hyperdjango.runtime.dispatcher import dispatch_page, dispatch_page_async


PANEL_PATH = "hyperdjango.integrations.debug_toolbar.panel.HyperDjangoPanel"
INTEGRATION_APP = "hyperdjango.integrations.debug_toolbar"
MIDDLEWARE = "debug_toolbar.middleware.DebugToolbarMiddleware"


def _ensure_settings() -> None:
    if settings.configured:
        return
    settings.configure(
        DEFAULT_CHARSET="utf-8",
        SECRET_KEY="test",
        ALLOWED_HOSTS=["*"],
        INSTALLED_APPS=[],
        MIDDLEWARE=[],
        TEMPLATES=[],
    )
    django.setup()


class _Store:
    def __init__(self) -> None:
        self.saved = {}

    def save_panel(self, request_id, panel_id, stats) -> None:
        self.saved[(request_id, panel_id)] = stats


class _Toolbar:
    def __init__(self, request) -> None:
        self.request = request
        self.stats = {}
        self.server_timing_stats = {}
        self.store = _Store()
        self.request_id = "request-id"


def _make_panel(request, get_response):
    _ensure_settings()
    from hyperdjango.integrations.debug_toolbar.panel import HyperDjangoPanel

    return HyperDjangoPanel(_Toolbar(request), get_response)


def _resolver(request, *, name="hyper_demo", route="demo/<int:id>/") -> None:
    request.resolver_match = SimpleNamespace(view_name=name, route=route)


@contextmanager
def _patched_settings(**values):
    with ExitStack() as stack:
        for name, value in values.items():
            stack.enter_context(patch.object(settings, name, value, create=True))
        yield


def test_optional_integration_import_does_not_import_debug_toolbar() -> None:
    script = """
import importlib.abc
import sys

class BlockDebugToolbar(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'debug_toolbar' or fullname.startswith('debug_toolbar.'):
            raise ImportError('blocked for optional dependency test')
        return None

sys.meta_path.insert(0, BlockDebugToolbar())
import hyperdjango
import hyperdjango.integrations.debug_toolbar as integration
assert integration.PANEL_PATH.endswith('HyperDjangoPanel')
assert 'debug_toolbar' not in sys.modules
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_panel_runs_inside_real_debug_toolbar_middleware() -> None:
    script = f"""
from types import SimpleNamespace

from django.conf import settings

settings.configure(
    DEBUG=True,
    SECRET_KEY='test',
    DEFAULT_CHARSET='utf-8',
    ALLOWED_HOSTS=['*'],
    INTERNAL_IPS=['127.0.0.1'],
    ROOT_URLCONF=__name__,
    STATIC_URL='/static/',
    INSTALLED_APPS=[
        'django.contrib.staticfiles',
        'debug_toolbar',
        'hyperdjango',
        '{INTEGRATION_APP}',
    ],
    MIDDLEWARE=['{MIDDLEWARE}'],
    TEMPLATES=[{{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
    }}],
    DEBUG_TOOLBAR_PANELS=['{PANEL_PATH}'],
    DEBUG_TOOLBAR_CONFIG={{
        'UPDATE_ON_FETCH': True,
        'IS_RUNNING_TESTS': False,
    }},
)

import django
django.setup()

from django.core.checks import run_checks
from django.http import HttpResponse
from django.test import RequestFactory
from debug_toolbar.middleware import DebugToolbarMiddleware
from debug_toolbar.toolbar import DebugToolbar, debug_toolbar_urls
from hyperdjango.runtime.dispatcher import dispatch_page

urlpatterns = debug_toolbar_urls()
captured = []
DebugToolbar._created.connect(
    lambda sender, toolbar, **kwargs: captured.append(toolbar), weak=False
)

class DemoPage:
    def get(self, request):
        return HttpResponse('<html><body>demo</body></html>')

request = RequestFactory().get('/demo/', REMOTE_ADDR='127.0.0.1')
request.resolver_match = SimpleNamespace(
    view_name='hyper_demo', route='demo/', namespaces=[]
)
middleware = DebugToolbarMiddleware(
    lambda current: dispatch_page(DemoPage(), current)
)
response = middleware(request)
assert b'djDebug' in response.content
panel = captured[0].get_panel_by_id('HyperDjangoPanel')
assert panel.get_stats()['route']['handler'] == 'get'
assert panel.get_stats()['is_hyperdjango'] is True
assert 'Route and handler' in panel.content
assert not [
    message for message in run_checks()
    if message.id.startswith('hyperdjango_debug_toolbar.')
]
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_panel_records_sync_route_action_redaction_result_and_timings() -> None:
    _ensure_settings()

    class DemoPage(HyperView):
        @action
        def save(self, request, **kwargs):
            return ActionResult(
                html="<div>saved</div>",
                target="#result",
                swap="inner",
                push_url="/done/",
            )

    request = RequestFactory().post(
        "/demo/7/",
        HTTP_X_HYPER_ACTION="save",
        HTTP_X_HYPER_TARGET="#result",
        HTTP_X_HYPER_DATA=(
            '{"title":"hello","password":"do-not-show",'
            '"nested":{"api_key":"also-secret"}}'
        ),
    )
    _resolver(request)
    panel = _make_panel(
        request,
        lambda current_request: dispatch_page(DemoPage(), current_request, id=7),
    )

    response = panel.process_request(request)
    panel.generate_stats(request, response)
    panel.generate_server_timing(request, response)
    stats = panel.get_stats()

    assert response.streaming is True
    assert stats["route"]["name"] == "hyper_demo"
    assert stats["route"]["pattern"] == "demo/<int:id>/"
    assert stats["route"]["page_class"] == (
        f"{DemoPage.__module__}.{DemoPage.__qualname__}"
    )
    assert stats["route"]["handler"] == "action:save"
    assert stats["route"]["parameters"] == {"id": 7}
    assert stats["route"]["source"]["file"] == __file__
    assert stats["route"]["source"]["display_file"] == "tests/test_debug_toolbar.py"
    assert stats["route"]["source"]["line"] > 0
    assert stats["route"]["details"]["directory"] == "tests"
    assert stats["route"]["details"]["page_file"] == "tests/test_debug_toolbar.py"
    assert stats["route"]["handler_mode"] == "sync"
    assert stats["route"]["handler_source"]["symbol"].endswith("DemoPage.save")
    assert stats["action"]["name"] == "save"
    assert stats["action"]["target"] == "#result"
    assert stats["action"]["arguments"]["title"] == "hello"
    assert stats["action"]["arguments"]["password"] == "[redacted]"
    assert stats["action"]["arguments"]["nested"]["api_key"] == "[redacted]"
    assert stats["action"]["source"]["file"] == __file__
    assert stats["action"]["source"]["symbol"].endswith("DemoPage.save")
    assert stats["action"]["mode"] == "sync"
    assert stats["results"][0]["item_types"] == ["History", "HTML"]
    assert stats["results"][0]["items"][0]["target"] == "#result"
    assert stats["response"]["content_type"].startswith("text/event-stream")
    assert {item["phase"] for item in stats["timings"]} >= {
        "dispatch",
        "action",
        "response preparation",
    }
    assert (
        panel.toolbar.server_timing_stats[panel.panel_id]["dispatch"]["title"]
        == "HyperDjango dispatch"
    )


def test_result_metadata_and_value_caps_are_bounded() -> None:
    from hyperdjango.actions import Event, Toast
    from hyperdjango.integrations.alpine.actions import Signal
    from hyperdjango.integrations.debug_toolbar.tracing import (
        describe_result,
        sanitize_value,
    )

    result = describe_result(
        [
            HTML(content="not included", target="#panel", swap="append"),
            History(push_url="/next/"),
            Redirect(url="/login/"),
        ]
    )

    assert result["item_types"] == ["HTML", "History", "Redirect"]
    assert result["items"] == [
        {
            "type": "HTML",
            "target": "#panel",
            "swap": "append",
            "content": "not included",
            "details": [],
        },
        {
            "type": "History",
            "push_url": "/next/",
            "details": [{"label": "push URL", "value": "/next/"}],
        },
        {
            "type": "Redirect",
            "url": "/login/",
            "details": [{"label": "URL", "value": "/login/"}],
        },
    ]
    assert sanitize_value("x" * 500).endswith("…")
    assert len(sanitize_value("x" * 500)) == 160
    long_html = describe_result(HTML(content="x" * 2000))
    assert len(long_html["items"][0]["content"]) == 1000
    assert long_html["items"][0]["content"].endswith("…")

    enriched = describe_result(
        [
            Signal(name="count", value=3),
            Event(name="saved", payload={"id": 7}),
            Toast(payload={"message": "Done", "access_token": "hidden"}),
        ]
    )
    assert enriched["items"][0]["details"] == [
        {"label": "name", "value": "count"},
        {"label": "value", "value": 3},
    ]
    assert enriched["items"][1]["details"][-1] == {
        "label": "payload",
        "value": {"id": 7},
    }
    assert enriched["items"][2]["payload"]["access_token"] == "[redacted]"


def test_exception_traceback_includes_source_frames_and_safe_locals() -> None:
    from hyperdjango.integrations.debug_toolbar.tracing import (
        record_exception,
        start_trace,
    )

    request = RequestFactory().get("/broken/")
    trace = start_trace(request)

    def fail():
        password = "do-not-show"
        visible = 7
        _ = password, visible
        raise ValueError("broken action")

    try:
        fail()
    except ValueError as exc:
        record_exception(request, exc, phase="action")

    exception = trace.exceptions[0]
    assert exception["type"] == "builtins.ValueError"
    assert exception["frames"]
    frame = exception["frames"][-1]
    assert frame["function"] == "fail"
    assert frame["locals"]["password"] == "[redacted]"
    assert frame["locals"]["visible"] == 7


def test_panel_records_full_page_render_details() -> None:
    _ensure_settings()

    class DemoPage(HyperView):
        def get(self, request):
            return {"title": "Demo"}

        @classmethod
        def get_template_name(cls):
            return "routes/demo/index.html"

        def _render_template_name(self, template_name, *, request, context):
            return f"<html><body>{context['title']}</body></html>"

    request = RequestFactory().get("/demo/")
    _resolver(request, route="demo/")
    panel = _make_panel(request, lambda current: dispatch_page(DemoPage(), current))

    response = panel.process_request(request)
    panel.generate_stats(request, response)
    render = panel.get_stats()["renders"][0]

    assert response.content == b"<html><body>Demo</body></html>"
    assert render["kind"] == "full page"
    assert render["template"] == "routes/demo/index.html"
    assert render["duration_ms"] >= 0


def test_panel_supports_async_dispatch_and_cleans_request_state() -> None:
    _ensure_settings()

    class DemoPage(HyperView):
        async def get(self, request):
            await asyncio.sleep(0)
            return HttpResponse("async")

    request = RequestFactory().get("/async/")
    _resolver(request, name="hyper_async", route="async/")

    async def get_response(current):
        return await dispatch_page_async(DemoPage(), current)

    panel = _make_panel(request, get_response)
    response = asyncio.run(panel.process_request(request))
    panel.generate_stats(request, response)

    assert response.content == b"async"
    assert panel.get_stats()["route"]["handler"] == "get"
    assert not hasattr(request, "_hyperdjango_debug_toolbar_trace")


def test_panel_observes_action_generator_only_during_stream_iteration() -> None:
    _ensure_settings()
    consumed = False

    class DemoPage(HyperView):
        @action
        def stream(self, request):
            def items():
                nonlocal consumed
                consumed = True
                yield HTML(content="<div>later</div>", target="#result")

            return items()

    request = RequestFactory().post("/stream/", HTTP_X_HYPER_ACTION="stream")
    _resolver(request, name="hyper_stream", route="stream/")
    panel = _make_panel(request, lambda current: dispatch_page(DemoPage(), current))

    response = panel.process_request(request)
    panel.generate_stats(request, response)
    result = panel.get_stats()["results"][0]

    assert consumed is False
    assert result["streaming"] is True
    assert result["item_types"] == ["Unknown until stream iteration"]
    assert result["iteration_status"] == "not started"
    assert result["note"] == "Stream iteration has not started."

    chunks = list(response.streaming_content)
    result = panel.get_stats()["results"][0]

    assert consumed is True
    assert chunks[-1].startswith(b"event: end")
    assert result["item_types"] == ["HTML"]
    assert result["items"][0]["target"] == "#result"
    assert result["iteration_status"] == "completed"
    assert result["note"] == "Stream iteration completed."
    assert not hasattr(request, "_hyperdjango_debug_toolbar_trace")
    stored = panel.toolbar.store.saved[(panel.toolbar.request_id, panel.panel_id)]
    assert stored["results"][0]["iteration_status"] == "completed"


def test_panel_observes_async_generator_after_stream_completion() -> None:
    _ensure_settings()

    class DemoPage(HyperView):
        @action
        def stream(self, request):
            async def items():
                await asyncio.sleep(0)
                yield History(push_url="/next/")
                yield HTML(content="<div>done</div>", target="#result")

            return items()

    request = RequestFactory().post("/stream/", HTTP_X_HYPER_ACTION="stream")
    request.scope = {}
    _resolver(request, name="hyper_stream", route="stream/")

    async def get_response(current):
        return await dispatch_page_async(DemoPage(), current)

    panel = _make_panel(request, get_response)

    async def consume():
        response = await panel.process_request(request)
        panel.generate_stats(request, response)
        before = panel.get_stats()["results"][0]["iteration_status"]
        chunks = [chunk async for chunk in response.streaming_content]
        return before, chunks

    before, chunks = asyncio.run(consume())
    result = panel.get_stats()["results"][0]

    assert before == "not started"
    assert chunks[-1].startswith(b"event: end")
    assert result["item_types"] == ["History", "HTML"]
    assert result["items"][0]["push_url"] == "/next/"
    assert result["items"][1]["target"] == "#result"
    assert result["iteration_status"] == "completed"
    assert not hasattr(request, "_hyperdjango_debug_toolbar_trace")


def test_panel_records_handled_hyperdjango_exceptions() -> None:
    _ensure_settings()

    class DemoPage(HyperView):
        @action
        def save(self, request):
            raise PermissionDenied("No access")

    request = RequestFactory().post("/demo/", HTTP_X_HYPER_ACTION="save")
    _resolver(request)
    panel = _make_panel(request, lambda current: dispatch_page(DemoPage(), current))

    response = panel.process_request(request)
    panel.generate_stats(request, response)
    exception = panel.get_stats()["exceptions"][0]

    assert response.status_code == 403
    assert exception["phase"] == "action"
    assert exception["type"].endswith("PermissionDenied")
    assert exception["message"] == "No access"
    assert "response preparation" in {
        timing["phase"] for timing in panel.get_stats()["timings"]
    }


def test_debug_toolbar_checks_are_silent_when_integration_is_not_enabled() -> None:
    _ensure_settings()
    from hyperdjango.integrations.debug_toolbar.checks import (
        check_debug_toolbar_configuration,
    )

    with _patched_settings(INSTALLED_APPS=[], MIDDLEWARE=[]):
        assert check_debug_toolbar_configuration(None) == []


def test_debug_toolbar_checks_report_common_misconfiguration() -> None:
    _ensure_settings()
    from hyperdjango.integrations.debug_toolbar.checks import (
        check_debug_toolbar_configuration,
    )

    with _patched_settings(
        INSTALLED_APPS=[INTEGRATION_APP],
        MIDDLEWARE=[],
        DEBUG_TOOLBAR_CONFIG={},
        DEBUG_TOOLBAR_PANELS=[],
    ):
        messages = check_debug_toolbar_configuration(None)

    assert [message.id for message in messages] == [
        "hyperdjango_debug_toolbar.W001",
        "hyperdjango_debug_toolbar.W002",
        "hyperdjango_debug_toolbar.W003",
    ]


def test_debug_toolbar_checks_accept_complete_configuration() -> None:
    _ensure_settings()
    from hyperdjango.integrations.debug_toolbar.checks import (
        check_debug_toolbar_configuration,
    )

    with _patched_settings(
        INSTALLED_APPS=[INTEGRATION_APP],
        MIDDLEWARE=[MIDDLEWARE],
        DEBUG_TOOLBAR_CONFIG={"UPDATE_ON_FETCH": True},
        DEBUG_TOOLBAR_PANELS=[PANEL_PATH],
    ):
        assert check_debug_toolbar_configuration(None) == []


def test_panel_template_is_valid_django_template() -> None:
    template_path = (
        Path(__file__).resolve().parent.parent
        / "hyperdjango"
        / "templates"
        / "hyperdjango"
        / "debug_toolbar"
        / "panel.html"
    )
    template = Engine().from_string(template_path.read_text())
    rendered = template.render(
        Context(
            {
                "is_hyperdjango": False,
                "route": {},
                "action": {},
                "renders": [],
                "results": [],
                "timings": [],
                "exceptions": [],
                "response": {},
            },
            use_l10n=False,
        )
    )
    assert "did not pass through HyperDjango dispatch" in rendered


def test_panel_template_renders_action_results_as_table_rows() -> None:
    template_path = (
        Path(__file__).resolve().parent.parent
        / "hyperdjango"
        / "templates"
        / "hyperdjango"
        / "debug_toolbar"
        / "panel.html"
    )
    template = Engine().from_string(template_path.read_text())
    rendered = template.render(
        Context(
            {
                "is_hyperdjango": True,
                "route": {},
                "action": {},
                "renders": [],
                "results": [
                    {
                        "kind": "list",
                        "streaming": False,
                        "item_types": ["HTML", "Redirect"],
                        "items": [
                            {
                                "type": "HTML",
                                "target": "#result",
                                "details": [],
                            },
                            {
                                "type": "Redirect",
                                "url": "/done/",
                                "details": [{"label": "URL", "value": "/done/"}],
                            },
                        ],
                    }
                ],
                "timings": [],
                "exceptions": [],
                "response": {},
            },
            use_l10n=False,
        )
    )

    assert "<th>Result</th>" in rendered
    assert "<th>Item</th>" in rendered
    assert "<th>Stream</th>" in rendered
    assert "<th>Target</th>" in rendered
    assert "<th>Swap</th>" in rendered
    assert "<th>Content</th>" in rendered
    assert "<th>Metadata</th>" in rendered
    assert "<code>HTML</code>" in rendered
    assert "<code>#result</code>" in rendered
    assert "<code>Redirect</code>" in rendered
    assert "<strong>URL:</strong> <code>/done/</code>" in rendered
    assert "<td>1.1</td>" in rendered
    results_section = rendered.split("<h4>Action results and SSE</h4>", 1)[1].split(
        "<h4>Phase timings</h4>", 1
    )[0]
    assert results_section.count("<tr>") == 3
    assert "<pre>" not in rendered
