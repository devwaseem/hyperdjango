from __future__ import annotations

import asyncio
import time
from pathlib import Path

import django
import pytest
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.template import Context, Engine
from django.test import override_settings
from django.test import RequestFactory
from django.views import View

from hyperdjango.actions import (
    Actions,
    ActionResult,
    Checkpoint,
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
from hyperdjango.runtime.responses import compile_action_result, to_action_http_response
from hyperdjango.sse import get_resume_checkpoint


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


def test_hyper_csp_nonce_template_tag_reads_request_nonce() -> None:
    engine = Engine(libraries={"hyper_tags": "hyperdjango.templatetags.hyper_tags"})
    template = engine.from_string("{% load hyper_tags %}{% hyper_csp_nonce %}")
    request = RequestFactory().get("/demo")
    setattr(request, "_csp_nonce", "test-nonce")

    assert template.render(Context({"request": request})) == "test-nonce"


def test_asset_tags_escape_attribute_values() -> None:
    rendered = str(
        ModuleTag(src='https://assets.example/app.js" onerror="alert(1)').render(
            nonce='safe" onclick="alert(1)'
        )
    )

    assert (
        'src="https://assets.example/app.js&quot; onerror=&quot;alert(1)"' in rendered
    )
    assert 'nonce="safe&quot; onclick=&quot;alert(1)"' in rendered
    assert '" onerror="' not in rendered
    assert '" onclick="' not in rendered


def test_base_template_adds_nonce_to_runtime_scripts() -> None:
    template = (
        Path(__file__).resolve().parent.parent
        / "hyperdjango"
        / "templates"
        / "hyperdjango"
        / "base.html"
    ).read_text()

    assert "{% hyper_csp_nonce as hyper_nonce %}" in template
    assert (
        "<script src=\"{% static 'hyperdjango/hyper.js' %}\""
        '{% if hyper_nonce %} nonce="{{ hyper_nonce }}"{% endif %}>'
    ) in template
    assert (
        "<script src=\"{% static 'hyperdjango/hyper-alpine.js' %}\""
        '{% if hyper_nonce %} nonce="{{ hyper_nonce }}"{% endif %}>'
    ) in template
    assert (
        "<script src=\"{% static 'hyperdjango/hyper-debug-toolbar.js' %}\""
        '{% if hyper_nonce %} nonce="{{ hyper_nonce }}"{% endif %}>'
    ) in template


def test_client_runtime_applies_nonce_to_dynamic_scripts() -> None:
    runtime = (
        Path(__file__).resolve().parent.parent
        / "hyperdjango"
        / "static"
        / "hyperdjango"
        / "hyper.js"
    ).read_text()

    assert "function currentScriptNonce() {" in runtime
    assert "script.nonce = nonce;" in runtime
    assert "const nonce = fromScript.nonce || currentScriptNonce();" in runtime


def test_debug_toolbar_bridge_refreshes_after_body_swaps() -> None:
    bridge = (
        Path(__file__).resolve().parent.parent
        / "hyperdjango"
        / "static"
        / "hyperdjango"
        / "hyper-debug-toolbar.js"
    ).read_text()

    assert 'window.addEventListener("hyper:settle:end"' in bridge
    assert 'document.getElementById("djDebug")' in bridge
    assert "window.djdt.show_toolbar();" in bridge
    assert 'window.addEventListener("hyper:afterRequest"' in bridge
    assert 'response.headers.get("djdt-request-id")' in bridge
    assert 'url.searchParams.set("panel_id", "HyperDjangoPanel")' in bridge
    assert "content.innerHTML = data.content;" in bridge


def test_client_runtime_uses_method_aware_sse_retry_defaults() -> None:
    runtime = (
        Path(__file__).resolve().parent.parent
        / "hyperdjango"
        / "static"
        / "hyperdjango"
        / "hyper.js"
    ).read_text()

    assert "sseRetry: true" in runtime
    assert 'return normalizeMethod(method) === "GET" && config.sseRetry;' in runtime
    assert "const retryEnabled = resolveSSERetry(method, options.sseRetry);" in runtime
    assert 'const retry = typeof options.retry === "boolean"' in runtime
    assert "const retryable = retryEnabled && expectSSE" in runtime
    assert "payload.retry" not in runtime
    assert "retry: switchedAction.retry" not in runtime
    assert "retry: resolveSSERetry(switchedAction.method)" in runtime


def test_client_runtime_exposes_native_network_state() -> None:
    runtime = (
        Path(__file__).resolve().parent.parent
        / "hyperdjango"
        / "static"
        / "hyperdjango"
        / "hyper.js"
    ).read_text()

    assert 'window.addEventListener("online"' in runtime
    assert 'window.addEventListener("offline"' in runtime
    assert 'emitEvent("hyper:network:change", detail)' in runtime
    assert '"hyper:network:online" : "hyper:network:offline"' in runtime
    assert 'root.querySelectorAll("[hyper-online]")' in runtime
    assert 'root.querySelectorAll("[hyper-offline]")' in runtime
    assert 'root.querySelectorAll("[hyper-online-class]")' in runtime
    assert 'root.querySelectorAll("[hyper-online-remove-class]")' in runtime
    assert 'root.querySelectorAll("[hyper-offline-class]")' in runtime
    assert 'root.querySelectorAll("[hyper-offline-remove-class]")' in runtime
    assert "await waitForNetwork(controller.signal);" in runtime
    assert "network," in runtime


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
        b'event: redirect\ndata: {"url": "/dashboard/"}\n\n'
    )


def test_action_http_response_redirect_never_replaces() -> None:
    items = compile_action_result(ActionResult(redirect_to="/dashboard/"))

    assert len(items) == 1
    assert isinstance(items[0], Redirect)
    assert items[0].url == "/dashboard/"


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
        b'event: redirect\ndata: {"url": "/done/"}\n\n'
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


def test_action_sse_checkpoints_allow_a_get_stream_to_resume() -> None:
    _ensure_settings()
    request = RequestFactory().get(
        "/demo",
        headers={"X-Hyper-Request-ID": "request-123"},
    )

    response = to_action_http_response(
        [
            Signal(name="count", value=1),
            Checkpoint("summary"),
            HTML(content="<div>Done</div>"),
            Checkpoint("complete"),
        ],
        request=request,
    )

    assert _read_streaming_response(response) == (
        b'event: patch_signals\ndata: {"count": 1}\n\n'
        b"event: checkpoint\nid: request-123:checkpoint:summary\n\n"
        b'event: patch_html\ndata: {"content": "<div>Done</div>", "swap": "outer"}\n\n'
        b"event: checkpoint\nid: request-123:checkpoint:complete\n\n"
        b"event: end\ndata: {}\n\n"
    )

    resumed_request = RequestFactory().get(
        "/demo",
        headers={
            "X-Hyper-Request-ID": "request-123",
            "Last-Event-ID": "request-123:checkpoint:summary",
        },
    )
    resume = get_resume_checkpoint(
        resumed_request,
        allowed=("summary", "complete"),
    )
    assert resume is not None
    assert (resume.name, resume.index) == ("summary", 0)

    resumed_response = to_action_http_response(
        [HTML(content="<div>Done</div>"), Checkpoint("complete")],
        request=resumed_request,
    )

    assert _read_streaming_response(resumed_response) == (
        b'event: patch_html\ndata: {"content": "<div>Done</div>", "swap": "outer"}\n\n'
        b"event: checkpoint\nid: request-123:checkpoint:complete\n\n"
        b"event: end\ndata: {}\n\n"
    )


@pytest.mark.parametrize(
    "last_event_id",
    [
        "",
        "another-request:checkpoint:summary",
        "request-123:1",
        "request-123:checkpoint:unknown",
        "request-123:checkpoint:has:colon",
    ],
)
def test_invalid_or_stale_resume_checkpoints_restart(
    last_event_id: str,
) -> None:
    request = RequestFactory().get(
        "/demo",
        headers={
            "X-Hyper-Request-ID": "request-123",
            "Last-Event-ID": last_event_id,
        },
    )

    assert get_resume_checkpoint(request, allowed=("summary", "complete")) is None


def test_resume_checkpoint_allow_list_must_be_unique() -> None:
    request = RequestFactory().get("/demo")

    with pytest.raises(ValueError, match="must be unique"):
        get_resume_checkpoint(request, allowed=("summary", "summary"))
    with pytest.raises(ValueError, match="ordered sequence"):
        get_resume_checkpoint(request, allowed="summary")  # type: ignore[arg-type]


def test_post_request_cannot_resume_a_checkpoint() -> None:
    request = RequestFactory().post(
        "/demo",
        headers={
            "X-Hyper-Request-ID": "request-123",
            "Last-Event-ID": "request-123:checkpoint:summary",
        },
    )

    assert get_resume_checkpoint(request, allowed=("summary",)) is None


def test_action_sse_checkpoints_require_get_and_unique_names() -> None:
    _ensure_settings()
    post_request = RequestFactory().post(
        "/demo",
        headers={"X-Hyper-Request-ID": "request-123"},
    )
    post_response = to_action_http_response(
        [Checkpoint("saved")],
        request=post_request,
    )
    with pytest.raises(ValueError, match="only supported for GET"):
        _read_streaming_response(post_response)

    get_request = RequestFactory().get(
        "/demo",
        headers={"X-Hyper-Request-ID": "request-123"},
    )
    duplicate_response = to_action_http_response(
        [Checkpoint("saved"), Checkpoint("saved")],
        request=get_request,
    )
    with pytest.raises(ValueError, match="emitted more than once"):
        _read_streaming_response(duplicate_response)

    invalid_id_request = RequestFactory().get(
        "/demo",
        headers={"X-Hyper-Request-ID": "invalid:request:id"},
    )
    invalid_id_response = to_action_http_response(
        [Checkpoint("saved")],
        request=invalid_id_request,
    )
    with pytest.raises(ValueError, match="valid X-Hyper-Request-ID"):
        _read_streaming_response(invalid_id_response)


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


def test_dispatch_page_ignores_get_action_query_parameter() -> None:
    class DemoPage(HyperView):
        @action
        def save(self, request, **params):
            return "action"

        def get(self, request, **params):
            return "page"

    request = RequestFactory().get("/demo", {"_action": "save"})

    response = dispatch_page(DemoPage(), request)

    assert response.status_code == 200
    assert response.content == b"page"


def test_dispatch_page_routes_post_action_from_form_field() -> None:
    class DemoPage(HyperView):
        @action
        def save(self, request, **params):
            return "ok"

    request = RequestFactory().post("/demo", {"_action": "save"})

    response = dispatch_page(DemoPage(), request)

    assert response.status_code == 200
    assert _read_streaming_response(response) == (
        b'event: patch_html\ndata: {"content": "ok", "swap": "outer"}\n\n'
        b"event: end\ndata: {}\n\n"
    )


def test_dispatch_page_supports_generator_actions() -> None:
    _ensure_settings()

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
        b'event: redirect\ndata: {"url": "/done/"}\n\n'
    )


def test_resumed_get_action_does_not_execute_completed_checkpoint_blocks() -> None:
    _ensure_settings()
    executed: list[str] = []
    checkpoints = ("summary", "rows")

    class DemoPage(HyperView):
        @action(method="GET")
        def watch(self, request, **params):
            resume = get_resume_checkpoint(request, allowed=checkpoints)
            completed = resume.index if resume else -1
            if completed < 0:
                executed.append("summary")
                yield HTML(content="summary")
                yield Checkpoint("summary")
            if completed < 1:
                executed.append("rows")
                yield HTML(content="rows")
                yield Checkpoint("rows")

    request = RequestFactory().get(
        "/demo",
        HTTP_X_HYPER_ACTION="watch",
        HTTP_X_HYPER_REQUEST_ID="watch-123",
        HTTP_LAST_EVENT_ID="watch-123:checkpoint:summary",
    )
    response = dispatch_page(DemoPage(), request)

    assert _read_streaming_response(response) == (
        b'event: patch_html\ndata: {"content": "rows", "swap": "outer"}\n\n'
        b"event: checkpoint\nid: watch-123:checkpoint:rows\n\n"
        b"event: end\ndata: {}\n\n"
    )
    assert executed == ["rows"]


def test_switch_action_is_typed_serialized_and_terminal_for_sync_streams() -> None:
    seen: list[str] = []

    class DemoPage(HyperView):
        @action(method="GET")
        def watch(self, request, job_id):
            return HTML(content=job_id)

    def items():
        yield HTML(content="before")
        yield DemoPage().watch.switch_to(job_id="42")
        seen.append("continued")
        yield HTML(content="after")

    response = to_action_http_response(items())

    assert _read_streaming_response(response) == (
        b'event: patch_html\ndata: {"content": "before", "swap": "outer"}\n\n'
        b'event: switch_action\ndata: {"name": "watch", "data": {"job_id": "42"}, '
        b'"method": "GET"}\n\n'
    )
    assert seen == []


def test_switch_action_is_terminal_for_async_streams() -> None:
    seen: list[str] = []

    class DemoPage(HyperView):
        @action(method="GET")
        def watch(self, request):
            return HTML(content="watching")

    async def items():
        yield DemoPage().watch.switch_to()
        seen.append("continued")
        yield HTML(content="after")

    response = to_action_http_response(items())

    assert _read_streaming_response(response) == (
        b'event: switch_action\ndata: {"name": "watch", "data": {}, '
        b'"method": "GET"}\n\n'
    )
    assert seen == []


def test_switch_depth_limit_returns_structured_action_error() -> None:
    _ensure_settings()

    class DemoPage(HyperView):
        @action
        def watch(self, request):
            return HTML(content="unreachable")

    request = RequestFactory().get(
        "/demo",
        HTTP_X_HYPER_ACTION="watch",
        HTTP_X_HYPER_SWITCH_DEPTH="3",
    )
    with override_settings(HYPER_SWITCH_ACTION_MAX_DEPTH=2):
        response = dispatch_page(DemoPage(), request)

    assert response.status_code == 409
    assert _read_streaming_response(response) == (
        b'event: error\ndata: {"status": 409, "message": '
        b'"Hyper action switch depth limit exceeded"}\n\n'
        b"event: end\ndata: {}\n\n"
    )


def test_dispatch_page_supports_async_generator_actions() -> None:
    _ensure_settings()

    class DemoPage(HyperView):
        @action
        async def save(self, request, **params):
            yield Signal(name="phase", value="starting")
            await asyncio.sleep(0)
            yield Signal(name="phase", value="done")

    request = RequestFactory().get("/demo", HTTP_X_HYPER_ACTION="save")
    response = dispatch_page(DemoPage(), request)

    assert response.status_code == 200
    assert _read_streaming_response(response) == (
        b'event: patch_signals\ndata: {"phase": "starting"}\n\n'
        b'event: patch_signals\ndata: {"phase": "done"}\n\n'
        b"event: end\ndata: {}\n\n"
    )


def test_sync_response_streams_async_generator_with_pause() -> None:
    _ensure_settings()

    class DemoPage(HyperView):
        @action
        async def save(self, request, **params):
            yield Signal(name="phase", value="start")
            await asyncio.sleep(0.2)
            yield Signal(name="phase", value="done")

    request = RequestFactory().get("/demo", HTTP_X_HYPER_ACTION="save")
    started = time.perf_counter()
    response = dispatch_page(DemoPage(), request)
    iterator = iter(response.streaming_content)

    first = next(iterator)
    first_at = time.perf_counter() - started
    second = next(iterator)
    second_at = time.perf_counter() - started
    third = next(iterator)

    assert first == b'event: patch_signals\ndata: {"phase": "start"}\n\n'
    assert second == b'event: patch_signals\ndata: {"phase": "done"}\n\n'
    assert third == b"event: end\ndata: {}\n\n"
    assert first_at < 0.15
    assert second_at >= 0.2


@override_settings(HYPER_SSE_HEARTBEAT_INTERVAL=0.02)
def test_sync_stream_emits_heartbeat_comments_while_generator_is_idle() -> None:
    _ensure_settings()

    def items():
        yield Signal(name="phase", value="start")
        time.sleep(0.06)
        yield Signal(name="phase", value="done")

    chunks = list(to_action_http_response(items()).streaming_content)

    assert chunks[0] == b'event: patch_signals\ndata: {"phase": "start"}\n\n'
    assert b": heartbeat\n\n" in chunks[1:-2]
    assert chunks[-2] == b'event: patch_signals\ndata: {"phase": "done"}\n\n'
    assert chunks[-1] == b"event: end\ndata: {}\n\n"


@override_settings(HYPER_SSE_HEARTBEAT_INTERVAL=0.02)
def test_wsgi_stream_emits_heartbeat_comments_for_async_generator() -> None:
    _ensure_settings()

    async def items():
        yield Signal(name="phase", value="start")
        await asyncio.sleep(0.06)
        yield Signal(name="phase", value="done")

    chunks = list(to_action_http_response(items()).streaming_content)

    assert chunks[0] == b'event: patch_signals\ndata: {"phase": "start"}\n\n'
    assert b": heartbeat\n\n" in chunks[1:-2]
    assert chunks[-2] == b'event: patch_signals\ndata: {"phase": "done"}\n\n'
    assert chunks[-1] == b"event: end\ndata: {}\n\n"


@override_settings(HYPER_SSE_HEARTBEAT_INTERVAL=0.02)
def test_asgi_stream_emits_heartbeat_comments_while_async_generator_is_idle() -> None:
    _ensure_settings()

    async def items():
        yield Signal(name="phase", value="start")
        await asyncio.sleep(0.06)
        yield Signal(name="phase", value="done")

    request = RequestFactory().get("/demo")
    request.scope = {}
    response = to_action_http_response(items(), request=request)

    async def consume() -> list[bytes]:
        return [chunk async for chunk in response.streaming_content]

    chunks = asyncio.run(consume())

    assert chunks[0] == b'event: patch_signals\ndata: {"phase": "start"}\n\n'
    assert b": heartbeat\n\n" in chunks[1:-2]
    assert chunks[-2] == b'event: patch_signals\ndata: {"phase": "done"}\n\n'
    assert chunks[-1] == b"event: end\ndata: {}\n\n"


@override_settings(HYPER_SSE_HEARTBEAT_INTERVAL=0.02)
def test_asgi_stream_emits_heartbeat_comments_for_sync_generator() -> None:
    _ensure_settings()

    def items():
        yield Signal(name="phase", value="start")
        time.sleep(0.06)
        yield Signal(name="phase", value="done")

    request = RequestFactory().get("/demo")
    request.scope = {}
    response = to_action_http_response(items(), request=request)

    async def consume() -> list[bytes]:
        return [chunk async for chunk in response.streaming_content]

    chunks = asyncio.run(consume())

    assert chunks[0] == b'event: patch_signals\ndata: {"phase": "start"}\n\n'
    assert b": heartbeat\n\n" in chunks[1:-2]
    assert chunks[-2] == b'event: patch_signals\ndata: {"phase": "done"}\n\n'
    assert chunks[-1] == b"event: end\ndata: {}\n\n"


@override_settings(HYPER_SSE_HEARTBEAT_INTERVAL=0)
def test_sse_heartbeats_can_be_disabled() -> None:
    _ensure_settings()

    def items():
        yield Signal(name="phase", value="start")
        time.sleep(0.03)
        yield Signal(name="phase", value="done")

    chunks = list(to_action_http_response(items()).streaming_content)

    assert b": heartbeat\n\n" not in chunks


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
