# Page API Reference

## `PageTemplate`

Base class for template/asset packaging without routing.

Primary methods:

- `render(request=..., context_updates=..., relative_template_name=...)`
- `render_block(block_name=..., request=..., context_updates=..., relative_template_name=...)`
- `get_template_name()`
- `get_relative_template_name(name)`

Use this for `hyper/templates/**` packages consumed by custom Django views.

## `HyperView`

`HyperView` extends `PageTemplate` with request/action behavior.

Adds:

- `dispatch(...)`
- `get(...)` / `post(...)` style handlers
- action registration via `@action`
- `action_response(...)`

Use this for routed pages under `hyper/routes/**/page.py`.

When a routed `PageView` subclasses Django `View`, route dispatch uses `as_view()` so `self.request` and normal Django CBV setup are available.

## `HyperActionMixin`

Mixin providing action registration and hypermedia response helpers.

Adds:

- `get_action(name)`
- `action_response(...)`

`HyperView` includes this mixin by default. You can also use it in non-routed custom view classes when you only need action semantics.

## `Page` (compatibility)

`Page` is a backward-compatible alias for `HyperView`.

## Shortcuts

### `render_template_page(...)`

```python
from hyperdjango.shortcuts import render_template_page
```

Renders a `PageTemplate` subclass into `HttpResponse`.

### `render_template_block(...)`

```python
from hyperdjango.shortcuts import render_template_block
```

Renders a named template block from a `PageTemplate` subclass into `HttpResponse`.
