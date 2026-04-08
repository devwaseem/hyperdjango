# Migration Guide: 0.3.0 -> 0.4.0

Version `0.4.0` focuses on route class behavior and Django CBV compatibility.

## What Changed

## 1) `HyperView` now subclasses Django `View`

`HyperView` now inherits `django.views.View`.

This means routed `PageView(HyperView)` classes use normal CBV lifecycle behavior (`self.request`, `args`, `kwargs`) while keeping Hyper actions and rendering helpers.

## 2) Route discovery uses class name `PageView`

Route loader now resolves route modules by class name (`PageView`) rather than scanning for `HyperView` subclasses.

Required in each route module:

```python
class PageView(...):
    ...
```

## 3) Plain Django views can be file-routed

Because route resolution is name-based and route dispatch now respects `as_view()` for Django `View` subclasses, this works:

```python
from django.views import View
from django.http import HttpResponse


class PageView(View):
    def get(self, request, **params):
        return HttpResponse("ok")
```

Use this when you want file routing without Hyper action behavior.

## Recommended Patterns

- Use `PageView(HyperView)` for Hyper actions, signals, swaps, and template helpers.
- Use `PageView(View)` for plain Django CBV behavior in file-routed modules.
- Use `HyperPageTemplate` for reusable non-routed template packages (`hyper/templates/**`).

## Checklist

- Ensure every `hyper/routes/**/+page.py` defines a class named `PageView`.
- For Hyper features, keep inheriting `HyperView`.
- For plain Django routes, subclass `django.views.View`.
- Run:

```bash
python manage.py hyper_routes
pytest
```
