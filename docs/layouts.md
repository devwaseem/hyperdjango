# Layouts

HyperDjango layouts live in `hyper/layouts/...`.

Pages use them by importing the layout class and inheriting from it explicitly.

## Layout Packages

This is the layout pattern HyperDjango supports.

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
