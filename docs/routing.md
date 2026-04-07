# Routing

HyperDjango discovers every `page.py` under `HYPER_FRONTEND_DIR/routes` and maps directory segments to Django URL patterns.

Each route module must define a class named `PageView`.

For Hyper features, `PageView` should inherit `HyperView`. For plain Django behavior, `PageView` can subclass `django.views.View`.

This routing model keeps route intent in the filesystem and reduces URLconf drift. You keep Django views/classes, with a predictable structure similar to file-routed frameworks.

## Segment Types

- `index` -> path passthrough (no URL segment)
- `about` -> static segment (`about`)
- `[slug]` -> dynamic segment (`<slug>`)
- `[...path]` -> catch-all segment (`<path:path>`)
- `(group)` -> route group (ignored in URL path)

## Examples

- `routes/index/page.py` -> `/`
- `routes/account/index/page.py` -> `/account`
- `routes/blog/[slug]/page.py` -> `/blog/<slug>`
- `routes/docs/[...path]/page.py` -> `/docs/<path:path>`
- `routes/(marketing)/pricing/page.py` -> `/pricing`

## Nested Layouts

Any `layout.py` in route ancestors is composed into the page class.

Layouts let you share shell code (navigation, wrappers, shared assets) while keeping inheritance explicit and server-side.

Example:

- `routes/layout.py`
- `routes/dashboard/layout.py`
- `routes/dashboard/settings/page.py`

`settings/page.py` inherits both layouts (outer to inner) plus its own page class.

## Conflict Detection

Compile-time conflicts are rejected:

Conflict detection makes ambiguous routes fail fast in development/CI instead of surfacing as production-only routing bugs.

- group collapse conflict: `(marketing)/pricing` vs `pricing`
- dynamic shape conflict: `[slug]` vs `[id]` at same level

Use `python manage.py hyper_routes` in CI to catch conflicts early.

## URL Prefix

`include_routes(url_prefix="app")` maps routes under `/app/*` without changing route files.

## Route Order

Compiled routes are sorted by specificity so static paths win before dynamic/catch-all matches.

## URL Reverse Names

HyperDjango assigns a Django URL `name` for each compiled route, so you can use Django `reverse()`.

Default naming:

- root (`/`) -> `hyper_index`
- `blog/[slug]` -> `hyper_blog_slug`
- `docs/[...path]` -> `hyper_docs_path_path`

Usage:

```python
from django.urls import reverse

reverse("hyper_blog_slug", kwargs={"slug": "hello"})
```

Custom route name:

```python
from hyperdjango.page import HyperView


class PageView(HyperView):
    route_name = "blog_detail"
```

Then:

```python
reverse("blog_detail", kwargs={"slug": "hello"})
```
