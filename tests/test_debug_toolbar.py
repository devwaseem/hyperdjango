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
    assert stats["route"] == {
        "name": "hyper_demo",
        "pattern": "demo/<int:id>/",
        "page_class": f"{DemoPage.__module__}.{DemoPage.__qualname__}",
        "handler": "action:save",
        "parameters": {"id": 7},
    }
    assert stats["action"]["name"] == "save"
    assert stats["action"]["target"] == "#result"
    assert stats["action"]["arguments"]["title"] == "hello"
    assert stats["action"]["arguments"]["password"] == "[redacted]"
    assert stats["action"]["arguments"]["nested"]["api_key"] == "[redacted]"
    assert stats["results"][0]["item_types"] == ["History", "HTML"]
    assert stats["results"][0]["items"][0]["target"] == "#result"
    assert stats["response"]["content_type"].startswith("text/event-stream")
    assert {item["phase"] for item in stats["timings"]} >= {
        "dispatch",
        "action",
        "response preparation",
    }
    assert panel.toolbar.server_timing_stats[panel.panel_id]["dispatch"][
        "title"
    ] == "HyperDjango dispatch"


def test_result_metadata_and_value_caps_are_bounded() -> None:
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
        {"type": "HTML", "target": "#panel", "swap": "append"},
        {"type": "History", "push_url": "/next/"},
        {"type": "Redirect", "url": "/login/"},
    ]
    assert sanitize_value("x" * 500).endswith("…")
    assert len(sanitize_value("x" * 500)) == 160


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


def test_panel_does_not_consume_action_generator_for_inspection() -> None:
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

    request = RequestFactory().post(
        "/stream/", HTTP_X_HYPER_ACTION="stream"
    )
    _resolver(request, name="hyper_stream", route="stream/")
    panel = _make_panel(request, lambda current: dispatch_page(DemoPage(), current))

    response = panel.process_request(request)
    panel.generate_stats(request, response)
    result = panel.get_stats()["results"][0]

    assert consumed is False
    assert result["streaming"] is True
    assert result["item_types"] == ["Unknown until stream iteration"]
    assert result["note"] == "The stream was not consumed for debugging."


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
            }
        )
    )
    assert "did not pass through HyperDjango dispatch" in rendered
