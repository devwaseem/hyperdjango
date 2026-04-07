from __future__ import annotations

from pathlib import Path

import django
from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory
from django.views import View

from hyperdjango.actions import ActionResult, action
from hyperdjango.page import HyperActionMixin, HyperView, Page, PageTemplate
from hyperdjango.routing.compiler import build_route_view


def test_page_is_backward_compatible_hyperview() -> None:
    assert issubclass(Page, HyperView)
    assert issubclass(HyperView, PageTemplate)
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
            return self.action_response(html="ok")

    obj = DemoMixin()
    method = obj.get_action("ping")
    assert method is not None
    result = method(None)
    assert isinstance(result, ActionResult)
    assert result.html == "ok"


def test_page_template_resolves_template_path(monkeypatch, tmp_path: Path) -> None:
    frontend_dir = tmp_path / "hyper"
    page_file = frontend_dir / "templates" / "profile_card" / "page.py"
    template_file = page_file.parent / "index.html"
    template_file.parent.mkdir(parents=True, exist_ok=True)
    page_file.write_text("# test")
    template_file.write_text("<div></div>")

    monkeypatch.setattr("hyperdjango.page.get_frontend_dir", lambda: frontend_dir)

    class ProfileCardTemplate(PageTemplate):
        @classmethod
        def _get_file_path(cls) -> str:
            return str(page_file)

    assert (
        ProfileCardTemplate.get_template_name() == "templates/profile_card/index.html"
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
