# Django Integration

## `include_routes(url_prefix="")`

Import:

```python
from hyperdjango.urls import include_routes
```

Usage:

```python
from django.contrib import admin
from django.urls import path

from hyperdjango.urls import include_routes

urlpatterns = [
    path("admin/", admin.site.urls),
    *include_routes(),
]
```

Arguments:

- `url_prefix: str = ""`
  Mount every compiled HyperDjango route under a prefix without changing the route files themselves.

Behavior:

- scans `HYPER_FRONTEND_DIR / "routes"` for `+page.py` files
- compiles route segments into Django `path(...)` or `re_path(...)` entries
- returns a list of URL patterns you can spread directly into `urlpatterns`

Notes:

- `url_prefix` is purely a mount-time prefix; it does not change route names or page classes
- if `APPEND_SLASH` is enabled, compiled routes include trailing slashes
- route conflicts are detected at compile time

## Django Debug Toolbar

For a complete walkthrough—including Docker, custom base templates, panel contents,
SSE limitations, system checks, and troubleshooting—see the
[Django Debug Toolbar guide](../debug-toolbar.md).

HyperDjango provides an optional first-class panel inside Django Debug Toolbar. It
also refreshes the toolbar after full-body navigation swaps. Django Debug Toolbar is
not a HyperDjango runtime dependency; install it only in development:

```bash
python -m pip install django-debug-toolbar
```

```python
# settings.py
if DEBUG:
    INSTALLED_APPS += [
        "debug_toolbar",
        "hyperdjango.integrations.debug_toolbar",
    ]
    MIDDLEWARE = [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        *MIDDLEWARE,
    ]
    INTERNAL_IPS = ["127.0.0.1"]
    DEBUG_TOOLBAR_CONFIG = {
        "UPDATE_ON_FETCH": True,
    }

    from debug_toolbar.settings import PANELS_DEFAULTS
    from hyperdjango.integrations.debug_toolbar import PANEL_PATH

    DEBUG_TOOLBAR_PANELS = list(PANELS_DEFAULTS)
    DEBUG_TOOLBAR_PANELS.insert(
        DEBUG_TOOLBAR_PANELS.index(
            "debug_toolbar.panels.templates.TemplatesPanel"
        )
        + 1,
        PANEL_PATH,
    )
```

If `GZipMiddleware` is enabled, put `DebugToolbarMiddleware` immediately after it;
otherwise keep Debug Toolbar near the start of the middleware list.

Placing `HyperDjangoPanel` after Django Debug Toolbar's Templates panel keeps the
request/rendering diagnostics together. The panel reports:

- compiled route, page class, HTTP handler, and route parameters
- action name, target, and arguments, with common password/token/secret fields redacted
- full-page, block, relative, and reusable-template renders
- action result and SSE item types plus target, swap, history, and redirect metadata
- dispatch, action, rendering, and response-preparation timings
- handled and unhandled HyperDjango exceptions

Streaming generators are never consumed for inspection. Their item types are shown as
unknown until stream iteration, while known `ActionResult`, `Actions`, list, and tuple
items are described immediately. The panel works for normal HTML responses and action
SSE responses; `UPDATE_ON_FETCH` lets the visible toolbar switch to the latest request.

Mount Debug Toolbar's URLs before HyperDjango's file-based routes:

```python
# urls.py
from django.conf import settings

from hyperdjango.urls import include_routes

urlpatterns = [
    *include_routes(),
]

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns = [*debug_toolbar_urls(), *urlpatterns]
```

Keep this configuration development-only. Follow Django Debug Toolbar's normal
installation guidance for conditional app, middleware, URL, and internal-IP setup.

### Configuration checks

Installing `hyperdjango.integrations.debug_toolbar` enables three Django system checks:

- `hyperdjango_debug_toolbar.W001`: `DebugToolbarMiddleware` is missing
- `hyperdjango_debug_toolbar.W002`: `UPDATE_ON_FETCH` is not `True`
- `hyperdjango_debug_toolbar.W003`: `HyperDjangoPanel` is absent from `DEBUG_TOOLBAR_PANELS`

The checks remain unregistered when the optional integration app is not installed.
