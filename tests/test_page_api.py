from __future__ import annotations

import asyncio
from pathlib import Path

import django
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import override_settings
from django.test import RequestFactory
from django.views import View

from hyperdjango.actions import (
    Actions,
    ActionResult,
    Delete,
    Event,
    HTML,
    Redirect,
    Signal,
    action,
)
from hyperdjango.assets import ModuleTag
from hyperdjango.page import (
    HyperActionMixin,
    HyperPageTemplate,
    HyperPartialTemplateResult,
    HyperView,
    Page,
)
from hyperdjango.routing.compiler import build_route_view
from hyperdjango.runtime.dispatcher import dispatch_page
from hyperdjango.runtime.responses import to_action_http_response


def _read_streaming_response(response) -> bytes:
    if hasattr(response, "streaming_content"):
        return b"".join(
            chunk if isinstance(chunk, bytes) else chunk.encode()
            for chunk in response.streaming_content
        )
    return response.content


def _ensure_settings() -> None:
    if settings.configured:
        return
    settings.configure(
        DEFAULT_CHARSET="utf-8",
        SECRET_KEY="test",
        ALLOWED_HOSTS=["*"],
    )
    django.setup()


def test_page_is_backward_compatible_hyperview() -> None:
    assert issubclass(Page, HyperView)
    assert issubclass(HyperView, HyperPageTemplate)
    assert issubclass(HyperView, View)


def test_page_template_get_context_accepts_request() -> None:
    _ensure_settings()

    class DemoTemplate(HyperPageTemplate):
        def get_context(self, request):
            return {"page": self, "request_path": request.path}

    page = DemoTemplate()
    request = RequestFactory().get("/demo")

    assert page.get_context(request)["request_path"] == "/demo"


def test_hyperview_registers_actions() -> None:
    class Demo(HyperView):
        @action
        def save(self, request):
            return "ok"

    page = Demo()
    assert page.get_action("save") is not None


def test_hyper_action_mixin_works_without_hyperview() -> None:
    class DemoMixin(HyperActionMixin):
        @action
        def ping(self, request):
            return self.action_response(content="ok")

    obj = DemoMixin()
    method = obj.get_action("ping")
    assert method is not None
    result = method(None)
    assert isinstance(result, ActionResult)
    assert result.html == "ok"


def test_action_response_supports_redirects() -> None:
    class DemoMixin(HyperActionMixin):
        @action
        def go(self, request):
            return self.action_response(redirect_to="/dashboard/")

    obj = DemoMixin()
    method = obj.get_action("go")
    assert method is not None

    result = method(None)

    assert isinstance(result, ActionResult)
    assert result.redirect_to == "/dashboard/"


def test_action_http_response_serializes_redirects() -> None:
    _ensure_settings()
    response = to_action_http_response(ActionResult(redirect_to="/dashboard/"))

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/event-stream")
    assert _read_streaming_response(response) == (
        b'event: redirect\ndata: {"url": "/dashboard/", "replace": false}\n\n'
    )


def test_action_response_accepts_partial_content() -> None:
    class DemoMixin(HyperActionMixin):
        pass

    obj = DemoMixin()
    result = obj.action_response(
        content=HyperPartialTemplateResult(
            html="<div>Modal</div>", js="/static/modal.js"
        )
    )

    assert isinstance(result, ActionResult)
    assert result.html == "<div>Modal</div>"
    assert result.js == "/static/modal.js"


def test_action_http_response_serializes_partial_js() -> None:
    _ensure_settings()
    response = to_action_http_response(
        ActionResult(html="<div>Modal</div>", js="/static/modal.js")
    )

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/event-stream")
    assert _read_streaming_response(response) == (
        b'event: patch_html\ndata: {"content": "<div>Modal</div>", "swap": "outer"}\n\n'
        b'event: load_js\ndata: {"src": "/static/modal.js"}\n\n'
        b"event: end\ndata: {}\n\n"
    )


def test_action_http_response_serializes_typed_item_lists() -> None:
    _ensure_settings()
    response = to_action_http_response(
        [Signal(name="count", value=1), HTML(content="<div>Hi</div>", target="#panel")]
    )

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/event-stream")
    assert _read_streaming_response(response) == (
        b'event: patch_signals\ndata: {"count": 1}\n\n'
        b'event: patch_html\ndata: {"content": "<div>Hi</div>", "swap": "outer", "target": "#panel"}\n\n'
        b"event: end\ndata: {}\n\n"
    )


def test_action_http_response_serializes_actions_wrapper() -> None:
    _ensure_settings()
    response = to_action_http_response(
        Actions(Signal(name="count", value=1), Redirect(url="/done/"))
    )

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/event-stream")
    assert _read_streaming_response(response) == (
        b'event: patch_signals\ndata: {"count": 1}\n\n'
        b'event: redirect\ndata: {"url": "/done/", "replace": false}\n\n'
    )


def test_action_http_response_serializes_delete_patch() -> None:
    _ensure_settings()
    response = to_action_http_response([Delete(target="#todo-1")])

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/event-stream")
    assert _read_streaming_response(response) == (
        b'event: patch_html\ndata: {"target": "#todo-1", "content": "", "swap": "delete"}\n\n'
        b"event: end\ndata: {}\n\n"
    )


def test_action_http_response_serializes_event_dispatch() -> None:
    _ensure_settings()
    response = to_action_http_response(
        [Event(name="profile:saved", payload={"id": 1}, target="#profile-panel")]
    )

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/event-stream")
    assert _read_streaming_response(response) == (
        b'event: dispatch_event\ndata: {"name": "profile:saved", "payload": {"id": 1}, "target": "#profile-panel"}\n\n'
        b"event: end\ndata: {}\n\n"
    )


def test_action_response_rejects_redirect_with_swap_fields() -> None:
    class DemoMixin(HyperActionMixin):
        pass

    obj = DemoMixin()

    try:
        obj.action_response(
            redirect_to="/dashboard/", html="<div>Saved</div>", target="#panel"
        )
    except ValueError as exc:
        assert str(exc) == (
            "action_response(redirect_to=...) cannot be combined with html, target"
        )
    else:
        raise AssertionError(
            "Expected action_response to reject redirect + swap fields"
        )


def test_action_response_rejects_error_statuses_except_422() -> None:
    class DemoMixin(HyperActionMixin):
        pass

    obj = DemoMixin()

    try:
        obj.action_response(content="nope", status=403)
    except ValueError as exc:
        assert str(exc) == (
            "action_response(status=...) only supports 2xx and 422 statuses; raise exceptions for 403/404/500"
        )
    else:
        raise AssertionError("Expected action_response to reject 403 status")


def test_page_template_resolves_template_path(monkeypatch, tmp_path: Path) -> None:
    frontend_dir = tmp_path / "hyper"
    page_file = frontend_dir / "templates" / "profile_card" / "page.py"
    template_file = page_file.parent / "index.html"
    template_file.parent.mkdir(parents=True, exist_ok=True)
    page_file.write_text("# test")
    template_file.write_text("<div></div>")

    monkeypatch.setattr("hyperdjango.page.get_frontend_dir", lambda: frontend_dir)

    class ProfileCardTemplate(HyperPageTemplate):
        @classmethod
        def _get_file_path(cls) -> str:
            return str(page_file)

    assert (
        ProfileCardTemplate.get_template_name() == "templates/profile_card/index.html"
    )


def test_page_template_renders_relative_template_directory(
    monkeypatch, tmp_path: Path
) -> None:
    frontend_dir = tmp_path / "hyper"
    page_file = frontend_dir / "routes" / "dashboard" / "+page.py"
    modal_dir = frontend_dir / "templates" / "modal"
    template_file = modal_dir / "index.html"
    entry_file = modal_dir / "entry.ts"
    page_file.parent.mkdir(parents=True, exist_ok=True)
    modal_dir.mkdir(parents=True, exist_ok=True)
    page_file.write_text("# test")
    template_file.write_text("<div>{{ title }}</div>")
    entry_file.write_text("import './modal.css';")

    monkeypatch.setattr("hyperdjango.page.get_frontend_dir", lambda: frontend_dir)
    monkeypatch.setattr(
        "hyperdjango.page.ViteAssetResolver.get_imports",
        lambda *, file: iter([ModuleTag(src=f"/static/{file}.js")]),
    )

    class DashboardPage(HyperPageTemplate):
        @classmethod
        def _get_file_path(cls) -> str:
            return str(page_file)

    page = DashboardPage()
    request = RequestFactory().get("/")
    _ensure_settings()
    with override_settings(
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [frontend_dir],
                "APP_DIRS": True,
                "OPTIONS": {"context_processors": []},
            }
        ]
    ):
        partial = page.render_template(
            "../../templates/modal",
            request=request,
            context_updates={"title": "Hello modal"},
        )

    assert partial == HyperPartialTemplateResult(
        html="<div>Hello modal</div>",
        js="/static/hyper/templates/modal/entry.ts.js",
    )


def test_dispatch_page_merges_get_context_with_get_result(
    monkeypatch, tmp_path: Path
) -> None:
    frontend_dir = tmp_path / "hyper"
    page_file = frontend_dir / "routes" / "dashboard" / "+page.py"
    template_file = page_file.parent / "index.html"
    page_file.parent.mkdir(parents=True, exist_ok=True)
    page_file.write_text("# test")
    template_file.write_text("<div>{{ base }} {{ title }}</div>")

    monkeypatch.setattr("hyperdjango.page.get_frontend_dir", lambda: frontend_dir)

    class DashboardPage(HyperPageTemplate):
        @classmethod
        def _get_file_path(cls) -> str:
            return str(page_file)

        def get_context(self, request):
            return {"page": self, "base": "Base"}

        def get(self, request, **params):
            return {"title": "Dashboard"}

    _ensure_settings()
    with override_settings(
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [frontend_dir],
                "APP_DIRS": True,
                "OPTIONS": {"context_processors": []},
            }
        ]
    ):
        response = dispatch_page(DashboardPage(), RequestFactory().get("/dashboard"))

    assert response.status_code == 200
    assert response.content == b"<div>Base Dashboard</div>"


def test_dispatch_page_routes_post_action_from_header() -> None:
    class DemoPage(HyperView):
        @action
        def save(self, request, **params):
            return "ok"

    request = RequestFactory().post(
        "/demo",
        HTTP_X_HYPER_ACTION="save",
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    response = dispatch_page(DemoPage(), request)

    assert response.status_code == 200
    assert _read_streaming_response(response) == (
        b'event: patch_html\ndata: {"content": "ok", "swap": "outer"}\n\n'
        b"event: end\ndata: {}\n\n"
    )


def test_dispatch_page_supports_generator_actions() -> None:
    class DemoPage(HyperView):
        @action
        def save(self, request, **params):
            yield Signal(name="phase", value="starting")
            yield Redirect(url="/done/")

    request = RequestFactory().get("/demo", HTTP_X_HYPER_ACTION="save")
    response = dispatch_page(DemoPage(), request)

    assert response.status_code == 200
    assert _read_streaming_response(response) == (
        b'event: patch_signals\ndata: {"phase": "starting"}\n\n'
        b'event: redirect\ndata: {"url": "/done/", "replace": false}\n\n'
    )


def test_dispatch_page_converts_permission_denied_to_error_event() -> None:
    class DemoPage(HyperView):
        @action
        def save(self, request, **params):
            raise PermissionDenied("Not allowed")

    request = RequestFactory().get("/demo", HTTP_X_HYPER_ACTION="save")
    response = dispatch_page(DemoPage(), request)

    assert response.status_code == 403
    assert _read_streaming_response(response) == (
        b'event: error\ndata: {"status": 403, "message": "Not allowed"}\n\n'
        b"event: end\ndata: {}\n\n"
    )


def test_route_view_uses_django_view_as_view_setup() -> None:
    if not settings.configured:
        settings.configure(
            DEFAULT_CHARSET="utf-8",
            SECRET_KEY="test",
            ALLOWED_HOSTS=["*"],
        )
        django.setup()

    class PageView(View):
        def get(self, request):
            return HttpResponse(b"True" if request is self.request else b"False")

    request = RequestFactory().get("/")
    view = build_route_view(PageView)
    response = view(request)

    assert response.status_code == 200
    assert response.content == b"True"


def test_route_view_supports_django_auth_mixins() -> None:
    _ensure_settings()

    class RequestCheckingMixin:
        def dispatch(self, request, *args, **kwargs):
            assert self.request is request
            return super().dispatch(request, *args, **kwargs)

    class PageView(RequestCheckingMixin, HyperView):
        def get(self, request):
            return HttpResponse(b"ok")

    request = RequestFactory().get("/")
    view = build_route_view(PageView)
    response = view(request)

    assert response.status_code == 200
    assert response.content == b"ok"


def test_route_view_supports_async_hyperview() -> None:
    _ensure_settings()

    class PageView(HyperView):
        async def get(self, request):
            assert self.request is request
            return HttpResponse(b"async ok")

    request = RequestFactory().get("/")
    view = build_route_view(PageView)
    response = asyncio.run(view(request))

    assert response.status_code == 200
    assert response.content == b"async ok"
