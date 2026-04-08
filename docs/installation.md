# Installation

Installation covers the two integration points that usually take the most time: wiring Django to file routes and wiring templates to modern JS assets. The scaffold command automates those steps so teams can start from working defaults.

Before setup, decide on your `hyper/` directory placement (commonly `BASE_DIR / "hyper"`). This is where layouts, routes, and route-local assets are co-located.

## Requirements

- Python `>=3.13`
- Django `>=4.2`
- Vite build output directory available at runtime

## 1) Install package

Package: `https://pypi.org/project/hyperdjango/`

From PyPI (recommended):

```bash
uv add hyperdjango
```

or:

```bash
pip install hyperdjango
```

## 2) Configure Django settings

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

Notes:

- `HYPER_FRONTEND_DIR` must exist and contain your `routes/` directory.
- `HYPER_VITE_OUTPUT_DIR` must exist when running with manifest assets.
- In dev mode, HyperDjango injects Vite client (`@vite/client`) in head imports.

## 3) Include routes

```python
from django.contrib import admin
from django.urls import path
from hyperdjango.urls import include_routes

urlpatterns = [
    path("admin/", admin.site.urls),
    *include_routes(),
]
```

With prefix:

```python
urlpatterns = [
    *include_routes(url_prefix="app"),
]
```

If you only use `HyperPageTemplate` packages from custom Django views, route inclusion is optional.

## 4) Scaffold starter files and JS tooling

```bash
python manage.py hyper_scaffold
```

Generated structure:

- `hyper/routes/index/+page.py`
- `hyper/routes/index/index.html`
- `hyper/templates/profile_card/page.py`
- `hyper/templates/profile_card/index.html`
- `hyper/layouts/base/layout.py`
- `hyper/layouts/base/index.html`
- `hyper/layouts/base/entry.ts`
- `hyper/shared/`

Also generated/updated:

- `vite.config.js`
- `package.json` (adds `vite`, `alpinejs`, `@alpinejs/morph`, `morphdom`, `vanilla-sonner`)
- `.gitignore` entries for `node_modules/` and `dist/`
- Django settings and urls module wiring (unless `--no-wire`)

Useful flags:

- `python manage.py hyper_scaffold --no-wire`
- `python manage.py hyper_scaffold --force`

## 5) Verify routes

```bash
python manage.py hyper_routes
python manage.py hyper_routes --json
```

## Development autoreload

When `runserver` is used, HyperDjango registers autoreload watchers for `HYPER_FRONTEND_DIR`.

Changes in `hyper/**` files (`.py`, `.html`, `.js`, `.ts`, `.css`, `.json`) trigger Django server reload automatically.
