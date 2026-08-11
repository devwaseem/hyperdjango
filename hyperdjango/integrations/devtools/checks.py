from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.checks import Warning, register
from django.urls import NoReverseMatch, reverse

from hyperdjango.integrations.devtools import MIDDLEWARE_PATH


@register()
def check_devtools_configuration(app_configs, **kwargs):
    del app_configs, kwargs
    if not getattr(settings, "HYPER_DEBUG_TOOLBAR", False):
        return []

    messages = []
    if MIDDLEWARE_PATH not in settings.MIDDLEWARE:
        messages.append(
            Warning(
                "HyperDjangoDebugToolbarMiddleware is missing.",
                hint=f"Add {MIDDLEWARE_PATH!r} near the start of MIDDLEWARE.",
                id="hyperdjango_devtools.W002",
            )
        )
    try:
        reverse("hyperdjango_devtools:history")
    except (AttributeError, ImproperlyConfigured, NoReverseMatch):
        messages.append(
            Warning(
                "HyperDjango Debug Toolbar URLs are not mounted.",
                hint=(
                    "Include 'hyperdjango.integrations.devtools.urls' before "
                    "HyperDjango file routes."
                ),
                id="hyperdjango_devtools.W003",
            )
        )
    return messages
