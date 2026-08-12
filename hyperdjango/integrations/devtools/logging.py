"""Opt-in logging helpers for the HyperDjango request inspector."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


DEFAULT_REQUEST_INSPECTOR_URL_PREFIX = "/__hyperdebug__/"


def _configured_url_prefix() -> str:
    try:
        config = getattr(settings, "HYPER_DEBUG_TOOLBAR_CONFIG", {})
    except ImproperlyConfigured:
        config = {}

    value: Any = DEFAULT_REQUEST_INSPECTOR_URL_PREFIX
    if isinstance(config, Mapping):
        value = config.get("URL_PREFIX", value)

    try:
        normalized = str(value).strip("/")
    except (TypeError, ValueError):
        normalized = ""
    if not normalized:
        normalized = DEFAULT_REQUEST_INSPECTOR_URL_PREFIX.strip("/")
    return f"/{normalized}"


def _safe_attribute(value: object, name: str) -> Any:
    try:
        return getattr(value, name, None)
    except Exception:
        return None


def _request_path(record: logging.LogRecord) -> str | None:
    request = _safe_attribute(record, "request")
    if request is None:
        return None

    for attribute in ("path_info", "path"):
        path = _safe_attribute(request, attribute)
        if isinstance(path, str) and path:
            return path
    return None


class RequestInspectorAccessLogFilter(logging.Filter):
    """Suppress ``django.server`` access logs for request-inspector endpoints.

    The filter is inert until a project explicitly attaches it to a logging
    handler. It neither changes logger names nor mutates Django's logging setup.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != "django.server":
            return True

        path = _request_path(record)
        if path is None:
            return True

        prefix = _configured_url_prefix()
        return not (path == prefix or path.startswith(f"{prefix}/"))


__all__ = [
    "DEFAULT_REQUEST_INSPECTOR_URL_PREFIX",
    "RequestInspectorAccessLogFilter",
]
