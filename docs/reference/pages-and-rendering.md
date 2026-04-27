# Pages and Rendering Reference

## `PageView`

In routed pages, `+page.py` must define a class named `PageView`.

That class can inherit from:

- `hyperdjango.page.HyperView`
- `django.views.View`

Requirements:

- the file must be named `+page.py`
- the class must be named `PageView`

## `HyperView`

Import:

```python
from hyperdjango.page import HyperView
```

`HyperView` inherits from:

- `HyperPageTemplate`
- `HyperActionMixin`
- Django `View`

That means a `HyperView` has both:

- template rendering APIs
- action registration and dispatch APIs

### `get_context(request)`

Signature:

```python
def get_context(self, request: HttpRequest) -> dict[str, Any]:
    ...
```

Purpose:

- build the base template context for the page
- usually extended with `super().get_context(request)`

### `render(request, relative_template_name="", context_updates=None)`

Signature:

```python
def render(
    self,
    *,
    request: HttpRequest,
    relative_template_name: str = "",
    context_updates: dict[str, Any] | None = None,
) -> str:
    ...
```

Arguments:

- `request`
  Current Django request
- `relative_template_name`
  Template path relative to the current page or template class directory. If omitted, `index.html` is used.
- `context_updates`
  Extra context merged on top of `get_context(request)`.

Returns:

- rendered HTML string

### `render_block(block_name, request, relative_template_name="", context_updates=None)`

Signature:

```python
def render_block(
    self,
    *,
    block_name: str,
    request: HttpRequest,
    relative_template_name: str = "",
    context_updates: dict[str, Any] | None = None,
) -> str:
    ...
```

Arguments:

- `block_name`
  Django template block name to render
- `request`
  Current Django request
- `relative_template_name`
  Optional relative template path. If omitted, the current page template is used.
- `context_updates`
  Extra context merged on top of the page context for this render only

Returns:

- rendered block HTML string

### `render_template(template_dir, request, context_updates=None)`

Signature:

```python
def render_template(
    self,
    template_dir: str,
    *,
    request: HttpRequest,
    context_updates: dict[str, Any] | None = None,
) -> HyperPartialTemplateResult:
    ...
```

Arguments:

- `template_dir`
  Directory relative to the current file location. HyperDjango expects `index.html` inside it.
- `request`
  Current Django request
- `context_updates`
  Extra context merged into the render

Returns:

- `HyperPartialTemplateResult`

Fields:

- `html: str`
- `js: str | None`

Limitation:

- action-time partial rendering only exposes HTML and one body JS entry path

## `HyperPageTemplate`

Import:

```python
from hyperdjango.page import HyperPageTemplate
```

Use it for standalone renderable template classes outside routed pages.

What it provides:

- template resolution relative to the class file
- inherited body/head/style/preload asset collection
- `page` in template context

### `get_template_name()`

Signature:

```python
@classmethod
def get_template_name(cls) -> str:
    ...
```

Purpose:
- Returns the full template name for the page's default `index.html` template.

### `get_relative_template_name(name)`

Signature:

```python
@classmethod
def get_relative_template_name(cls, name: str) -> str:
    ...
```

Arguments:
- `name: str`
  The relative file name (e.g., `"index.html"`, `"partial.html"`).

Purpose:
- Converts a relative template name to a full Django template name, relative to the class location.

### `resolve_import(file_name)`

Signature:

```python
@classmethod
def resolve_import(cls, *, file_name: str) -> Generator[AssetTag, None, None]:
    ...
```

Arguments:
- `file_name: str`
  The entry file to resolve (e.g., `"entry.js"`, `"entry.head.ts"`).

Purpose:
- Resolves Vite imports for a given entry file, yielding `AssetTag` objects (`ModuleTag`, `StyleSheetTag`, `ModulePreloadTag`).

Raises:
- `FileNotFoundError`: If the file does not exist.
- `FileNotLoadedFromViteError`: If the file exists but was not included in the Vite manifest.

## Shortcuts

```python
from hyperdjango.shortcuts import render_template_block, render_template_page
```

### `render_template_page(request, template_cls, context=None, status=200, headers=None)`

Renders a standalone `HyperPageTemplate` class as a full Django `HttpResponse`.

**Arguments:**

- `request` (`HttpRequest`): The current Django request object.
- `template_cls` (`type[HyperPageTemplate]`): The template class to render.
- `context` (`dict[str, Any] | None`): Initial context data to pass to the template. Default: `None`.
- `status` (`int`): HTTP status code for the response. Default: `200`.
- `headers` (`dict[str, str] | None`): Additional HTTP headers to include in the response. Default: `None`.

**Returns:**

- `HttpResponse` containing the rendered HTML.

### `render_template_block(request, template_cls, block_name, context=None, relative_template_name="", status=200, headers=None)`

Renders a specific template block from a `HyperPageTemplate` class as a full Django `HttpResponse`.

**Arguments:**

- `request` (`HttpRequest`): The current Django request object.
- `template_cls` (`type[HyperPageTemplate]`): The template class to render.
- `block_name` (`str`): The name of the Django template block (e.g., `{% block content %}`) to render.
- `context` (`dict[str, Any] | None`): Initial context data to pass to the template. Default: `None`.
- `relative_template_name` (`str`): Optional relative path to a specific template file if not using the class default. Default: `""`.
- `status` (`int`): HTTP status code for the response. Default: `200`.
- `headers` (`dict[str, str] | None`): Additional HTTP headers to include in the response. Default: `None`.

**Returns:**

- `HttpResponse` containing the rendered block HTML.
