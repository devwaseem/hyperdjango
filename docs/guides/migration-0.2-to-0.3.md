# Migration Guide: 0.2.0 -> 0.3.0

This release introduces API and routing conventions that may require code updates.

## Breaking Changes

## 1) Routed classes must be named `PageView`

Every `hyper/routes/**/page.py` module must define:

```python
class PageView(HyperView):
    ...
```

Previous class names like `HomePage`, `ProfilePage`, etc. are no longer discovered for route compilation.

## 2) `Page` is split into `PageTemplate` + `HyperView`

New model:

- `PageTemplate`: rendering + assets (`render`, `render_block`, template path helpers)
- `HyperView`: routed request/action behavior
- `Page`: backward-compatible alias of `HyperView`

For routed pages, prefer importing `HyperView` explicitly.

## 3) New `HyperActionMixin`

Action behavior is now reusable via `HyperActionMixin`.

- `HyperView` includes it by default
- custom classes can opt into action behavior without being routed pages

## Migration Steps

## A) Rename routed classes to `PageView`

Before:

```python
class AboutPage(HyperView):
    ...
```

After:

```python
class PageView(HyperView):
    ...
```

## B) Update imports for clarity

Recommended:

```python
from hyperdjango.page import HyperView
```

`Page` still works, but `HyperView` makes intent explicit.

## C) Move non-routed reusable UI to `PageTemplate`

Use `hyper/templates/**` for template packages consumed by custom Django views.

```python
from hyperdjango.page import PageTemplate


class ProfileCardTemplate(PageTemplate):
    pass
```

## D) Optional: use shortcuts

```python
from hyperdjango.shortcuts import render_template_page, render_template_block
```

These helpers render `PageTemplate` classes directly to `HttpResponse`.

## Common Errors

## `No PageView class found in ...`

Cause: route module does not define `PageView`.

Fix: rename the routed class to `PageView`.

## Route compiles but behavior changed unexpectedly

Run:

```bash
python manage.py hyper_routes
```

Confirm each route maps to the expected module and class.

## Checklist

- Rename all routed classes to `PageView`
- Use `HyperView` in `hyper/routes/**`
- Use `PageTemplate` in `hyper/templates/**`
- Run tests + `python manage.py hyper_routes`
