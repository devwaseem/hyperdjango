# Routing

HyperDjango scans `hyper/routes/` for `+page.py` files and turns folders into Django URL patterns.

The best way to learn routing is to start with static and dynamic routes first, then move to typed, regex, and catch-all patterns.

## Basic Route Structure

Each route directory usually contains:

- `+page.py`
- `index.html`

`+page.py` must define a class named `PageView`.

```python
from __future__ import annotations

from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request: HttpRequest) -> dict[str, str]:
        return {"title": "About"}
```

## Static Routes

Examples:

- `hyper/routes/index/+page.py` -> `/`
- `hyper/routes/about/+page.py` -> `/about/`

## Nested Routes

Routes nest by nesting folders.

```text
hyper/routes/
  dashboard/
    index/
      +page.py
    settings/
      +page.py
    users/
      [id]/
        +page.py
```

This produces:

- `/dashboard/`
- `/dashboard/settings/`
- `/dashboard/users/<id>/`

## Dynamic Parameters

Use square brackets for dynamic params.

`hyper/routes/blog/[slug]/+page.py`:

```python
from __future__ import annotations

from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request: HttpRequest, slug: str) -> dict[str, str]:
        return {"slug": slug}
```

## Typed Parameters

Use Django path converters with the portable `__` separator.

- `[int__id]`
- `[slug__slug]`
- `[path__path]`

```python
from __future__ import annotations

from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request: HttpRequest, id: int) -> dict[str, int]:
        return {"user_id": id}
```

## Regex Parameters

If built-in converters are not enough, use inline regex syntax:

```text
[name__regex]
```

Example:

```text
hyper/routes/invites/[code__[A-Z0-9]{8}]/+page.py
```

```python
from __future__ import annotations

from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request: HttpRequest, code: str) -> dict[str, str]:
        return {"code": code}
```

## Composite Segments

One URL segment can contain multiple captured values and literals.

Examples:

- `[uidb36]-[key]`
- `[kind]-v[version]`
- `[uidb36__[0-9A-Za-z]+]-[key__.+]`

```python
from __future__ import annotations

from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request: HttpRequest, uidb36: str, key: str) -> dict[str, str]:
        return {"uidb36": uidb36, "key": key}
```

## Catch-All Parameters

Use `[...path]` for catch-all paths.

```text
hyper/routes/docs/[...path]/+page.py
```

```python
from __future__ import annotations

from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request: HttpRequest, path: str) -> dict[str, object]:
        parts = [part for part in path.split("/") if part]
        return {"raw_path": path, "parts": parts}
```

## Route Groups

Use `(group)` to organize routes without affecting the public URL.

```text
hyper/routes/(marketing)/pricing/+page.py
```

This compiles to `/pricing/`.

## Reverse Names

HyperDjango generates Django URL names automatically.

- `hyper/routes/blog/[slug]/+page.py` -> `hyper_blog_slug`
- `hyper/routes/docs/[...path]/+page.py` -> `hyper_docs_path_path`

You can override it:

```python
from __future__ import annotations

from hyperdjango.page import HyperView


class PageView(HyperView):
    route_name = "blog_detail"
```

## Prefixes and Slash Behavior

`include_routes(url_prefix="app")` mounts all compiled routes under `/app/`.

Compiled route generation also respects Django `APPEND_SLASH` behavior.

## Conflict Detection

HyperDjango rejects ambiguous route shapes at compile time.

Use `python manage.py hyper_routes` in CI to catch conflicts early.
