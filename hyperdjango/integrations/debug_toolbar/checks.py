from __future__ import annotations

from django.conf import settings
from django.core.checks import Warning, register

from hyperdjango.integrations.debug_toolbar import PANEL_PATH


DEBUG_TOOLBAR_MIDDLEWARE = "debug_toolbar.middleware.DebugToolbarMiddleware"


@register()
def check_debug_toolbar_configuration(app_configs, **kwargs):
    """Validate configuration only when the optional integration app is loaded."""
    installed_apps = list(getattr(settings, "INSTALLED_APPS", []))
    if not any(
        app == "hyperdjango.integrations.debug_toolbar"
        or app.startswith("hyperdjango.integrations.debug_toolbar.apps.")
        for app in installed_apps
    ):
        return []
    warnings = []
    middleware = list(getattr(settings, "MIDDLEWARE", []))
    panels = list(getattr(settings, "DEBUG_TOOLBAR_PANELS", []))
    config = dict(getattr(settings, "DEBUG_TOOLBAR_CONFIG", {}))

    if DEBUG_TOOLBAR_MIDDLEWARE not in middleware:
        warnings.append(
            Warning(
                "HyperDjango's Debug Toolbar integration requires "
                "DebugToolbarMiddleware.",
                hint=f"Add {DEBUG_TOOLBAR_MIDDLEWARE!r} to MIDDLEWARE.",
                id="hyperdjango_debug_toolbar.W001",
            )
        )
    if config.get("UPDATE_ON_FETCH") is not True:
        warnings.append(
            Warning(
                "HyperDjango navigation requires Debug Toolbar fetch updates.",
                hint="Set DEBUG_TOOLBAR_CONFIG['UPDATE_ON_FETCH'] = True.",
                id="hyperdjango_debug_toolbar.W002",
            )
        )
    if PANEL_PATH not in panels:
        warnings.append(
            Warning(
                "The HyperDjango panel is missing from DEBUG_TOOLBAR_PANELS.",
                hint=f"Add {PANEL_PATH!r} to DEBUG_TOOLBAR_PANELS.",
                id="hyperdjango_debug_toolbar.W003",
            )
        )
    return warnings
