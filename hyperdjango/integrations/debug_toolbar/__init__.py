"""Optional Django Debug Toolbar integration for HyperDjango.

This package is safe to import without ``django-debug-toolbar`` installed. The
panel module itself is imported only when explicitly listed in
``DEBUG_TOOLBAR_PANELS``.
"""

PANEL_PATH = "hyperdjango.integrations.debug_toolbar.panel.HyperDjangoPanel"

__all__ = ["PANEL_PATH"]
