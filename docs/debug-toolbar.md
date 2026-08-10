# Django Debug Toolbar

HyperDjango includes an optional panel for Django Debug Toolbar. It stays inside the
normal Debug Toolbar UI and follows both full-page requests and HyperDjango action/SSE
requests.

Use it to answer questions such as:

- which file-based route and `PageView` handled this request?
- which action ran, with which target and non-sensitive arguments?
- which templates or blocks rendered, and how long did they take?
- which `HTML`, `History`, `Redirect`, or other action items were returned?
- where did dispatch, action execution, rendering, or response preparation spend time?
- did HyperDjango catch an exception and turn it into an action error response?

`django-debug-toolbar` remains optional and is not installed with HyperDjango.

## Install the development dependency

Install Django Debug Toolbar in your development environment:

```bash
python -m pip install django-debug-toolbar
```

Do not add it to the dependencies used by production deployments.

## Configure `settings.py`

Enable both Django Debug Toolbar and the HyperDjango integration app only in
development:

```python
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
```

`UPDATE_ON_FETCH` is required for the visible toolbar to switch to the most recent
HyperDjango navigation or action request.

The Debug Toolbar middleware should be near the start of `MIDDLEWARE`. If you use
`django.middleware.gzip.GZipMiddleware`, put `DebugToolbarMiddleware` immediately
after it so the toolbar sees the uncompressed response.

### Docker development

For Docker-based development, Django Debug Toolbar can discover the Docker host:

```python
DEBUG_TOOLBAR_CONFIG = {
    "UPDATE_ON_FETCH": True,
    "SHOW_TOOLBAR_CALLBACK": (
        "debug_toolbar.middleware.show_toolbar_with_docker"
    ),
}
```

Keep `DEBUG = False` in production even when using a custom callback.

## Add the HyperDjango panel

Defining `DEBUG_TOOLBAR_PANELS` replaces Debug Toolbar's default panel list, so retain
the defaults and insert `HyperDjangoPanel`. Placing it immediately after the Templates
panel keeps rendering diagnostics together:

```python
if DEBUG:
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

The explicit panel path is:

```python
"hyperdjango.integrations.debug_toolbar.panel.HyperDjangoPanel"
```

## Mount Debug Toolbar URLs

Mount Debug Toolbar's URLs before `include_routes()`. This prevents a broad
file-based route from intercepting the `__debug__` endpoints:

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

You can place admin or other explicit project URLs between the Debug Toolbar and
HyperDjango routes.

## Keep the toolbar across HyperDjango navigation

The default HyperDjango base template loads a small bridge that re-shows Django Debug
Toolbar after a full `<body>` swap:

```django
{% extends "hyperdjango/base.html" %}
```

If your project owns the entire base document instead, load the bridge after
`hyper.js`:

```django
{% load static %}

<script src="{% static 'hyperdjango/hyper.js' %}"></script>
<script src="{% static 'hyperdjango/hyper-debug-toolbar.js' %}"></script>
```

Projects using a CSP nonce should apply the same nonce to both scripts. The shipped
`hyperdjango/base.html` does this automatically through `{% hyper_csp_nonce %}`.

## Use the panel

Start Django and your Vite development server normally, then:

1. Open a HyperDjango page from an IP allowed by Django Debug Toolbar.
2. Expand the Django Debug Toolbar.
3. Select **HyperDjango**.
4. Navigate with `hyper-nav` or submit a HyperDjango action.
5. Reopen the panel to inspect the latest request.

With `UPDATE_ON_FETCH=True`, action requests appear even though their response is an
SSE stream rather than a complete HTML page.

## Read the panel

### Route and handler

Shows the compiled Django route name and pattern, the fully qualified page class,
the HTTP handler, and sanitized route parameters. Action requests use a handler label
such as `action:save`.

### Action

Shows the action name, requested target, and merged action arguments. Arguments include
values supplied through `X-Hyper-Data`, form/query data, and route parameters.

Common password, token, secret, cookie, CSRF, API-key, access-key, and private-key
fields are displayed as `[redacted]`. Long strings and representations are capped.
The panel is a debugging aid, not a substitute for Django's production secret-handling
and exception-reporting controls.

### Rendering

Lists each recorded render operation:

- `full page`: the route's main `index.html`
- `relative template`: a page-local template passed to `render()`
- `block`: a `render_block()` operation, including the block name
- `reusable template`: a template package rendered with `render_template()`

Each row includes the template name and render duration.

### Action results and SSE

Known action results report item types and useful metadata, including targets, swap
modes, history URLs, redirects, event names, and loaded script URLs.

HyperDjango does not iterate a generator merely to populate the panel. For a sync or
async generator, the panel reports **Unknown until stream iteration**. Consequently,
the panel can measure stream construction and response preparation, but not the later
time spent yielding every SSE item to the client.

### Phase timings

Timings are request-local and measured in milliseconds:

- `dispatch`: complete HyperDjango dispatch
- `action`: action handler execution up to obtaining its result
- `render`: an individual template or block render
- `response preparation`: conversion into an `HttpResponse` or SSE response

The dispatch duration is also exposed through the standard `Server-Timing` response
header when the panel is enabled.

### Exceptions

Shows exceptions observed during HyperDjango dispatch or action handling. This includes
`PermissionDenied`, `Http404`, and unexpected action exceptions that HyperDjango turns
into structured SSE error responses.

## Validate the setup

Run Django's system checks:

```bash
python manage.py check
```

Installing `hyperdjango.integrations.debug_toolbar` enables these checks:

- `hyperdjango_debug_toolbar.W001`: `DebugToolbarMiddleware` is missing
- `hyperdjango_debug_toolbar.W002`: `UPDATE_ON_FETCH` is not `True`
- `hyperdjango_debug_toolbar.W003`: `HyperDjangoPanel` is missing from
  `DEBUG_TOOLBAR_PANELS`

The checks are not registered when the optional integration app is absent.

## Troubleshooting

### The entire toolbar is missing

Check that:

- `DEBUG` is `True`
- `debug_toolbar` is in `INSTALLED_APPS`
- `DebugToolbarMiddleware` is installed in the correct order
- the browser's IP is in `INTERNAL_IPS`, or the Docker callback is configured
- the response is HTML and contains a closing `</body>` tag
- Debug Toolbar's URL patterns are mounted

### The toolbar appears, but there is no HyperDjango panel

Check that:

- `hyperdjango.integrations.debug_toolbar` is in `INSTALLED_APPS`
- `PANEL_PATH` is present in `DEBUG_TOOLBAR_PANELS`
- Django template app-directory loading is enabled (`APP_DIRS=True` or the equivalent
  app-directories loader)
- the server was restarted after changing settings

### The panel says “No dispatch”

The request was observed by Django Debug Toolbar but did not pass through
`dispatch_page_sync()` or `dispatch_page_async()`. This is expected for admin pages,
static files, Debug Toolbar's own endpoints, and ordinary non-HyperDjango views.

### Panel data is stale after navigation or actions

Check that:

- `DEBUG_TOOLBAR_CONFIG["UPDATE_ON_FETCH"]` is exactly `True`
- the body-swap bridge is loaded when using a custom base document
- the Debug Toolbar middleware receives the HyperDjango request
- the browser is not serving a cached page or stale static script

### SSE item types are unknown

This is expected for generator and async-generator action results. HyperDjango avoids
consuming the stream because doing so would change application behavior. Return a known
`ActionResult`, `Actions`, list, or tuple when you want item metadata to be available
before streaming begins.

## Production safety

Django Debug Toolbar is a development tool and can expose settings, SQL, headers,
template context, and request data. Do not enable the toolbar, its URLs, or the
HyperDjango integration app on public production deployments.
