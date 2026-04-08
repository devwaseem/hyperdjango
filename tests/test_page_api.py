from __future__ import annotations

from pathlib import Path

import django
from django.conf import settings
from django.http import HttpResponse
from django.test import override_settings
from django.test import RequestFactory
from django.views import View

from hyperdjango.actions import ActionResult, action
from hyperdjango.assets import ModuleTag
from hyperdjango.page import (
    HyperActionMixin,
    HyperPageTemplate,
    HyperPartialTemplateResult,
    HyperView,
    Page,
)
from hyperdjango.routing.compiler import build_route_view
from hyperdjango.runtime.responses import to_action_http_response


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
    assert response["Content-Type"] == "application/json"
    assert response.content == b'{"redirect_to": "/dashboard/"}'


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
    assert response["Content-Type"] == "application/json"
    assert response.content == b'{"js": "/static/modal.js", "html": "<div>Modal</div>"}'


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
