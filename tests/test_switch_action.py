from __future__ import annotations

import json

import django
import pytest
from django.conf import settings
from django.test import RequestFactory, override_settings
from django.urls import path

from hyperdjango.actions import HTML, SwitchAction, action
from hyperdjango.page import HyperView
from hyperdjango.runtime.dispatcher import dispatch_page


def _ensure_settings() -> None:
    if settings.configured:
        return
    settings.configure(
        DEFAULT_CHARSET="utf-8",
        SECRET_KEY="test",
        ALLOWED_HOSTS=["*"],
        ROOT_URLCONF=__name__,
    )
    django.setup()


def _read_stream(response) -> bytes:
    return b"".join(
        chunk if isinstance(chunk, bytes) else chunk.encode()
        for chunk in response.streaming_content
    )


class DestinationPage(HyperView):
    @action(method="GET")
    def watch_build(self, request, package_id: str, job_id: str):
        return HTML(content=f"{package_id}:{job_id}")


class OtherPage(HyperView):
    @action(method="GET")
    def unrelated(self, request):
        return HTML(content="unrelated")


class SourcePage(HyperView):
    @action(method="POST")
    def start_build(self, request, package_id: str):
        return DestinationPage.watch_build.at(
            "build-detail",
            route_kwargs={"package_id": package_id},
            query={"panel": "status"},
        ).switch_to(job_id="job-42")


urlpatterns = [
    path("source/<str:package_id>/", SourcePage.as_view(), name="build-source"),
    path(
        "builds/<str:package_id>/",
        DestinationPage.as_view(),
        name="build-detail",
    ),
    path("other/", OtherPage.as_view(), name="other"),
]


def test_bound_action_switch_to_builds_internal_switch_action() -> None:
    page = DestinationPage()
    setattr(page, "_hyper_action_route_params", {"package_id": "pkg-1"})

    result = page.watch_build.switch_to(job_id="job-1")

    assert isinstance(result, SwitchAction)
    assert result.resolve() == (
        "watch_build",
        {"job_id": "job-1"},
        "GET",
        None,
    )


def test_switch_to_uses_the_decorated_wire_name() -> None:
    class NamedPage(HyperView):
        @action("build_status", method="GET")
        def watch_build(self, request, job_id: str):
            return HTML(content=job_id)

    result = NamedPage().watch_build.switch_to(job_id="job-1")

    assert result.resolve()[0] == "build_status"


def test_switch_to_validates_destination_signature() -> None:
    page = DestinationPage()
    setattr(page, "_hyper_action_route_params", {"package_id": "pkg-1"})

    with pytest.raises(TypeError, match="missing a required argument: 'job_id'"):
        page.watch_build.switch_to()
    with pytest.raises(TypeError, match="unexpected keyword argument 'unknown'"):
        page.watch_build.switch_to(job_id="job-1", unknown=True)
    with pytest.raises(TypeError, match="duplicate route parameters: package_id"):
        page.watch_build.switch_to(package_id="other", job_id="job-1")


def test_switch_destination_requires_declared_transport_metadata() -> None:
    class LegacyPage(HyperView):
        @action
        def watch(self, request):
            return HTML(content="watch")

    with pytest.raises(TypeError, match="must declare method="):
        LegacyPage().watch.switch_to()


def test_cross_endpoint_switch_reverses_and_validates_route_owner() -> None:
    _ensure_settings()
    request = RequestFactory().post(
        "/source/pkg-1/",
        HTTP_X_HYPER_ACTION="start_build",
        HTTP_X_HYPER_DATA=json.dumps({"package_id": "ignored"}),
    )

    with override_settings(ROOT_URLCONF=__name__):
        response = dispatch_page(SourcePage(), request, package_id="pkg-1")
        body = _read_stream(response)

    assert body == (
        b'event: switch_action\ndata: {"name": "watch_build", "data": '
        b'{"job_id": "job-42"}, "method": "GET", '
        b'"url": "/builds/pkg-1/?panel=status"}\n\n'
    )


def test_cross_endpoint_switch_rejects_an_action_from_another_page() -> None:
    _ensure_settings()
    with override_settings(ROOT_URLCONF=__name__):
        with pytest.raises(ValueError, match="does not belong to route 'other'"):
            DestinationPage.watch_build.at(
                "other",
                route_kwargs={},
            ).switch_to(package_id="pkg", job_id="job")


def test_declared_action_method_is_enforced() -> None:
    _ensure_settings()
    request = RequestFactory().post(
        "/builds/pkg-1/",
        HTTP_X_HYPER_ACTION="watch_build",
        HTTP_X_HYPER_DATA=json.dumps({"job_id": "job-1"}),
    )

    response = dispatch_page(DestinationPage(), request, package_id="pkg-1")

    assert response.status_code == 405
    assert _read_stream(response) == (
        b'event: error\ndata: {"status": 405, "message": '
        b"\"Action 'watch_build' requires GET\"}\n\n"
        b"event: end\ndata: {}\n\n"
    )
