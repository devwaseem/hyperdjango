# Getting Started

This page gets one complete HyperDjango page working first.

Start here before reading the deeper routing, rendering, action, and client-side pages.

## Requirements

- Python `>=3.13`
- Django `>=4.2`
- Node.js `>=20.19` when developing or building frontend assets with Vite 8
- Vite build output available at runtime

## Install

```bash
pip install hyperdjango
```

Add `hyperdjango` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "hyperdjango",
]
```

## Configure Django

```python
HYPER_FRONTEND_DIR = BASE_DIR / "hyper"
HYPER_VITE_OUTPUT_DIR = BASE_DIR / "dist"
HYPER_DEV = DEBUG

TEMPLATES[0]["DIRS"].append(HYPER_FRONTEND_DIR)
STATICFILES_DIRS = [HYPER_VITE_OUTPUT_DIR]
```

What these do:

- `HYPER_FRONTEND_DIR`: where HyperDjango finds `routes/`, `layouts/`, `templates/`, and shared frontend files
- `HYPER_VITE_OUTPUT_DIR`: where Vite writes built assets
- `HYPER_DEV`: whether to use development assets or manifest-built production assets

`hyper_runserver` discovers Vite's runtime URL automatically. Set the optional
`HYPER_VITE_DEV_SERVER_URL` only when using development assets with another
server workflow.

## Mount Routes

```python
from django.contrib import admin
from django.urls import path

from hyperdjango.urls import include_routes

urlpatterns = [
    path("admin/", admin.site.urls),
    *include_routes(),
]
```

You can optionally mount them under a prefix:

```python
urlpatterns = [
    *include_routes(url_prefix="app"),
]
```

## Scaffold a Starter Project

```bash
python manage.py hyper_scaffold
```

This creates a starter `hyper/` tree, Vite config, and basic page/layout/template examples.

Useful flags:

- `python manage.py hyper_scaffold --no-wire`
- `python manage.py hyper_scaffold --force`

## Your First Page

Create `hyper/routes/about/+page.py`:

```python
from __future__ import annotations

from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request: HttpRequest) -> dict[str, str]:
        return {"title": "About"}
```

Create `hyper/routes/about/index.html`:

```django
<h1>{{ title }}</h1>
<p>This page was rendered by HyperDjango.</p>
```

That route is now available at `/about/`.

## Your First Action

Update `hyper/routes/about/+page.py`:

```python
from __future__ import annotations

from django.http import HttpRequest

from hyperdjango.actions import HTML, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request: HttpRequest) -> dict[str, object]:
        return {"title": "About", "count": 0}

    @action
    def increment(self, request: HttpRequest, count: int = 0):
        next_count = int(count) + 1
        return [HTML(content=f"<span id='count'>{next_count}</span>", target="#count")]
```

Update `hyper/routes/about/index.html`:

```django
<h1>{{ title }}</h1>
<p>Count: <span id="count">{{ count }}</span></p>
<button type="button" @click="$action('increment', { count })">Increment</button>
```

## Verify Routes

```bash
python manage.py hyper_routes
python manage.py hyper_routes --json
```

## Optional Development Diagnostics

HyperDjango ships its own rich request inspector for routes, actions, rendering,
timings, exceptions, and completed SSE streams. See
[HyperDjango Debug Toolbar](dev-toolbar.md) for setup. `DEBUG=True` is recommended,
but `HYPER_DEBUG_TOOLBAR` is the authoritative enablement switch so consumers can
choose their own environment and access policy.

An optional [Django Debug Toolbar panel](debug-toolbar.md) remains available for
projects already using DJDT.
