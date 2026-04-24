# Layouts

HyperDjango has two layout patterns.

Use `hyper/layouts/...` for explicit reusable layouts.

Use route-local `layout.py` when a whole route subtree should inherit shared behavior automatically.

## Reusable Layout Packages

This is the clearest pattern for most projects.

Example structure:

```text
hyper/
  layouts/
    base/
      __init__.py
      index.html
      entry.ts
  routes/
    about/
      +page.py
      index.html
```

`hyper/layouts/base/__init__.py`:

```python
from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from hyperdjango.page import HyperView


class BaseLayout(HyperView):
    def get_context(self, request: HttpRequest) -> dict[str, Any]:
        context = super().get_context(request)
        context["site_name"] = "HyperDjango Example"
        return context
```

`hyper/layouts/base/index.html`:

```django
{% extends "hyperdjango/base.html" %}

{% block body %}
  <nav>{{ site_name }}</nav>
  <main>{% block page %}{% endblock page %}</main>
{% endblock body %}
```

`hyper/layouts/base/entry.ts`:

```ts
import Alpine from "alpinejs";
import "./base.css";

Alpine.start();
```

`hyper/routes/about/+page.py`:

```python
from __future__ import annotations

from django.http import HttpRequest

from hyper.layouts.base import BaseLayout


class PageView(BaseLayout):
    def get(self, request: HttpRequest) -> dict[str, str]:
        return {"title": "About", "content": "This page inherits BaseLayout."}
```

`hyper/routes/about/index.html`:

```django
{% extends "layouts/base/index.html" %}

{% block page %}
  <h1>{{ title }}</h1>
  <p>{{ content }}</p>
{% endblock page %}
```

## What Layout Packages Are For

Use them for:

- shared template shells
- shared Python helpers
- shared `get_context()` data
- shared `entry.ts` / `entry.head.ts`
- shared CSS imported by those entries

## Route-Local `layout.py`

Use route-local layouts when a whole route subtree should share behavior automatically.

Example structure:

```text
hyper/routes/
  dashboard/
    layout.py
    reports/
      +page.py
      index.html
```

`dashboard/layout.py` must:

- be named exactly `layout.py`
- define a `HyperView` subclass
- not use any special class name

The router walks upward from the page directory and composes any matching route-local layout classes it finds.

The nearest route-local layout takes precedence over parent route-local layouts.

Use this pattern for section-wide defaults. Use `hyper/layouts/...` when you want a reusable layout package that can be imported explicitly.
