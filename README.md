# HyperDjango

Build interactive Django apps without splitting your product into "backend API + SPA frontend".

HyperDjango keeps rendering and business logic on the server, then layers in partial swaps, signals, OOB updates, and transitions for SPA-like UX.

## Problem -> Approach -> Outcome

- Problem: teams duplicate feature logic across Django views, API serializers, and frontend state stores.
- Approach: treat HTML as the interface, organize features in `hyper/`, and use actions for incremental updates.
- Outcome: one feature implementation path with fast interactions and fewer moving parts.

## Why This Works

- Keep business logic in Django, not duplicated across REST + frontend app layers.
- Get SPA-like interactions (partial swaps, OOB updates, toasts, transitions) with HTML as the transport.
- Organize by feature using file-based routes and co-located templates/assets.

## Locality of Behavior

HyperDjango is centered around a single `hyper/` directory where routes, layouts, and frontend entry files live together.

```text
hyper/
  layouts/
    base/
      __init__.py
      index.html
      entry.ts
  routes/
    index/
      page.py
      index.html
      partials/
        flash.html
    todos/
      page.py
      index.html
      partials/
        item.html
  shared/
    __init__.py
```

Each route folder owns its behavior:

- `page.py`: server logic (`get/post/@action`)
- `index.html`: page template
- `partials/*`: fragments used by action swaps
- nearby `entry.ts` files: route/layout-specific client assets

This keeps the code you change for a feature close together.

## What You Get

- file-based routing from `hyper/routes/**/page.py`
- nested `layout.py` composition
- class-based pages with native `get/post/...` handlers
- `@action` methods for hypermedia interactions
- Alpine-friendly `$get` / `$post` client helpers
- progressive enhancement for links/forms (`hyper-nav`, `hyper-form`)
- native Vite integration (dev server + build manifest)

## Install

Package: `https://pypi.org/project/hyperdjango/`

From PyPI (recommended):

```bash
uv add hyperdjango
```

or:

```bash
pip install hyperdjango
```

## Quick Start

1) Add app + settings:

```python
INSTALLED_APPS = [
    # ...
    "hyperdjango",
]

HYPER_FRONTEND_DIR = BASE_DIR / "hyper"
HYPER_VITE_OUTPUT_DIR = BASE_DIR / "dist"
HYPER_VITE_DEV_SERVER_URL = "http://localhost:5173/"
HYPER_DEV = DEBUG

TEMPLATES[0]["DIRS"].append(HYPER_FRONTEND_DIR)
STATICFILES_DIRS = [HYPER_VITE_OUTPUT_DIR]
```

2) Scaffold HyperDjango into your existing project:

```bash
python manage.py hyper_scaffold
```

This generates `hyper/` directories (including `routes/`, `templates/`, `layouts/`), starter files, `vite.config.js`, and `package.json` dependencies/scripts. By default it also wires your Django settings + urls file. Use `--no-wire` to skip patching, or `--force` to overwrite scaffolded files.

3) If you used `--no-wire`, mount routes manually in `urls.py`:

```python
from django.contrib import admin
from django.urls import path
from hyperdjango.urls import include_routes

urlpatterns = [
    path("admin/", admin.site.urls),
    *include_routes(),
]
```

4) Run route introspection:

```bash
python manage.py hyper_routes
```

## Basic Page

```python
from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request):
        return {"title": "About"}
```

Place this in `hyper/routes/about/page.py` and create `hyper/routes/about/index.html`.

Note: each `hyper/routes/**/page.py` must define a class named `PageView` (typically inheriting `HyperView`).

## Actions

Use `@action` for partial updates, signal patches, toasts, OOB updates, and swap control.

```python
from hyperdjango.actions import action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def add(self, request, title=""):
        html = self.render_block(
            request=request,
            block_name="todo_list",
            context_updates={"items": [title]},
        )
        return self.action_response(
            html=html,
            target="#todo-list",
            swap="inner",
            toast={"type": "success", "message": "Added"},
        )
```

## Use PageTemplate Without Routes

If you do not want file-based URL routing for a feature, create a template package in `hyper/templates/**` and render it from your own Django view.

```python
from hyperdjango.page import PageTemplate


class ProfileCardTemplate(PageTemplate):
    pass
```

```python
from hyperdjango.shortcuts import render_template_page


def profile_card(request):
    return render_template_page(request, ProfileCardTemplate, context={"title": "Account"})
```

## Client Runtime

HyperDjango exposes helpers globally and as Alpine magics:

- `window.get(...)` and `window.post(...)`
- Alpine: `$get(...)` and `$post(...)`

```html
<div x-data="{ q: '' }">
  <input x-model="q" />
  <button x-on:click="$get('search', { q }, { target: '#results', key: 'search' })">
    Search
  </button>
</div>
```

## Route Naming Conventions

- `routes/index/page.py` -> `/`
- `routes/about/page.py` -> `/about`
- `routes/blog/[slug]/page.py` -> `/blog/<slug>`
- `routes/docs/[...path]/page.py` -> `/docs/<path:path>`
- `routes/(marketing)/pricing/page.py` -> `/pricing`

## Template Tags

Load tags:

```django
{% load hyper_tags %}
```

Available tags:

- `hyper_preloads`
- `hyper_stylesheets`
- `hyper_head_scripts`
- `hyper_body_scripts`
- `hyper_custom_entry "name"`

## Docs

- ReadTheDocs structure is configured via `.readthedocs.yaml` and `docs/conf.py`.
- Docs sections are split into Guides, Reference, and Examples/Cookbook.

- [Docs Index](docs/index.md)
- [Installation](docs/installation.md)
- [Migration 0.2 -> 0.3](docs/guides/migration-0.2-to-0.3.md)
- [Custom Base Template](docs/guides/custom-base-template.md)
- [Vite Production Build](docs/guides/vite-production-build.md)
- [Template Packages](docs/guides/template-packages.md)
- [Config Reference](docs/config-reference.md)
- [Page API](docs/reference/page-api.md)
- [Routing](docs/routing.md)
- [Pages and Actions](docs/pages-and-actions.md)
- [Signals](docs/signals.md)
- [Runtime Reference](docs/runtime-reference.md)
- [Forms](docs/forms.md)
- [Events](docs/events.md)
- [Cookbook](docs/cookbook.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Production Checklist](docs/production-checklist.md)

## Example App

A full runnable demo lives in `example/`.

- setup and run instructions: [example/README.md](example/README.md)
- includes routes for static, dynamic, catch-all, grouped, nested layouts
- includes action-heavy examples: `/todos`, `/search`, `/profile`
