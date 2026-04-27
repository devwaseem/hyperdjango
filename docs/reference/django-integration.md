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
