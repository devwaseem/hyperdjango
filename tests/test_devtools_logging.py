from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import patch

from hyperdjango.integrations.devtools.logging import (
    RequestInspectorAccessLogFilter,
)


def _record(
    path: str | None = None,
    *,
    path_info: str | None = None,
    logger_name: str = "django.server",
) -> logging.LogRecord:
    record = logging.LogRecord(
        logger_name,
        logging.INFO,
        __file__,
        1,
        '"GET / HTTP/1.1" 200 42',
        (),
        None,
    )
    record.request = SimpleNamespace(path=path, path_info=path_info)
    return record


def test_filter_suppresses_default_request_inspector_prefix() -> None:
    access_filter = RequestInspectorAccessLogFilter()

    assert access_filter.filter(_record(path_info="/__hyperdebug__")) is False
    assert (
        access_filter.filter(_record(path_info="/__hyperdebug__/requests/abc/"))
        is False
    )


def test_filter_suppresses_normalized_custom_prefix() -> None:
    settings = SimpleNamespace(
        HYPER_DEBUG_TOOLBAR_CONFIG={"URL_PREFIX": "/internal/inspector/"}
    )

    with patch("hyperdjango.integrations.devtools.logging.settings", settings):
        access_filter = RequestInspectorAccessLogFilter()
        assert access_filter.filter(_record(path_info="/internal/inspector")) is False
        assert (
            access_filter.filter(_record(path_info="/internal/inspector/history/"))
            is False
        )
        assert access_filter.filter(_record(path_info="/__hyperdebug__/history/"))


def test_filter_preserves_record_without_request() -> None:
    record = _record(path_info="/__hyperdebug__/history/")
    del record.request

    assert RequestInspectorAccessLogFilter().filter(record) is True


def test_filter_preserves_record_when_request_has_no_usable_path() -> None:
    assert RequestInspectorAccessLogFilter().filter(_record()) is True


def test_filter_preserves_unrelated_and_lookalike_paths() -> None:
    access_filter = RequestInspectorAccessLogFilter()

    assert access_filter.filter(_record(path_info="/assets/app.css")) is True
    assert access_filter.filter(_record(path_info="/__hyperdebugger__/history/")) is True


def test_filter_preserves_normal_page_and_action_logs() -> None:
    access_filter = RequestInspectorAccessLogFilter()

    assert access_filter.filter(_record(path_info="/")) is True
    assert access_filter.filter(_record(path_info="/orders/42/")) is True


def test_filter_falls_back_to_request_path() -> None:
    assert (
        RequestInspectorAccessLogFilter().filter(
            _record(path="/__hyperdebug__/history/")
        )
        is False
    )


def test_filter_prefers_path_info_over_path() -> None:
    record = _record(path="/__hyperdebug__/history/", path_info="/orders/42/")

    assert RequestInspectorAccessLogFilter().filter(record) is True


def test_filter_does_not_suppress_records_from_other_loggers() -> None:
    record = _record(
        path_info="/__hyperdebug__/history/",
        logger_name="hyperdjango.application",
    )

    assert RequestInspectorAccessLogFilter().filter(record) is True
    assert record.name == "hyperdjango.application"
