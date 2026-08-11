"""Development-first HyperDjango request inspector."""

from django.conf import settings

APP_NAME = "hyperdjango.integrations.devtools"
MIDDLEWARE_PATH = (
    "hyperdjango.integrations.devtools.middleware.HyperDjangoDebugToolbarMiddleware"
)
URL_NAMESPACE = "hyperdjango_devtools"


def is_enabled() -> bool:
    """Return whether the explicitly configured inspector may serve requests."""
    return bool(getattr(settings, "HYPER_DEBUG_TOOLBAR", False))


__all__ = ["APP_NAME", "MIDDLEWARE_PATH", "URL_NAMESPACE", "is_enabled"]
