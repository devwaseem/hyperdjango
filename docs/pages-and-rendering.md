# Pages and Rendering

Pages and rendering APIs belong together because they all answer the same question: how does a `PageView` turn server-side state into HTML?

## `HyperView`

`HyperView` is the main page class for routed pages.

It combines:

- Django `View` dispatch
- template rendering
- action dispatch
- page-level asset awareness

Minimal example:

```python
from __future__ import annotations

from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request: HttpRequest) -> dict[str, str]:
        return {"title": "Home"}
```

`hyper/routes/index/index.html`:

```django
<h1>{{ title }}</h1>
```

## Plain Django `View`

If you only want file-based routing, `PageView` can be a normal Django `View` subclass.

```python
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.views import View


class PageView(View):
    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        return HttpResponse(f"Post: {slug}")
```

Use plain `View` when routing is the only HyperDjango feature you need for that page.

## `get_context()`

Use `get_context()` for values you want on every request for that page.

```python
from __future__ import annotations

from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def get_context(self, request: HttpRequest) -> dict[str, object]:
        context = super().get_context(request)
        context["site_name"] = "HyperDjango Demo"
        return context

    def get(self, request: HttpRequest) -> dict[str, str]:
        return {"title": "Dashboard"}
```

## `render()`

Use `render()` to render a template relative to the current page or template class.

```python
from __future__ import annotations

from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def preview(self, request: HttpRequest) -> str:
        return self.render(
            request=request,
            relative_template_name="partials/preview.html",
            context_updates={"message": "Hello"},
        )
```

This is ideal for page-local partials such as `partials/form.html` or `partials/result.html`.

## `render_block()`

Use `render_block()` when you want one named block from a template.

```python
from __future__ import annotations

from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def todo_list_html(self, request: HttpRequest) -> str:
        return self.render_block(
            request=request,
            block_name="todo_list",
            context_updates={"items": ["Write docs", "Ship feature"]},
        )
```

## `render_template()`

Use `render_template()` when you want to render a self-contained directory that contains:

- `index.html`
- optional `entry.ts` or `entry.js`

```python
from __future__ import annotations

from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def modal_partial(self, request: HttpRequest):
        return self.render_template(
            "partials/confirm_modal",
            request=request,
            context_updates={"title": "Confirm", "message": "Continue?"},
        )
```

This returns a `HyperPartialTemplateResult` with:

- `html`
- optional `js`

Important limitation: this result does not separately expose head scripts, stylesheets, or preloads. It is designed for action-time HTML + optional JS insertion.

## `HyperPageTemplate`

Use `HyperPageTemplate` for standalone renderable template classes outside routed pages.

```python
from __future__ import annotations

from hyperdjango.page import HyperPageTemplate


class ProfileCardTemplate(HyperPageTemplate):
    pass
```

That gives the template package:

- template resolution relative to the Python file
- the `page` object in context
- nearby entry discovery
- asset metadata for template tags

`HyperView` already inherits from `HyperPageTemplate`.

## `render_template_page()`

Use `render_template_page()` to render a standalone template class as a normal Django response.

```python
from __future__ import annotations

from django.http import HttpRequest, HttpResponse

from hyper.templates.profile_card.page import ProfileCardTemplate
from hyperdjango.shortcuts import render_template_page


def profile_card(request: HttpRequest) -> HttpResponse:
    return render_template_page(
        request,
        ProfileCardTemplate,
        context={"name": "Waseem", "role": "Engineer"},
    )
```

## `render_template_block()`

Use `render_template_block()` when you only need one block from a standalone template class.

```python
from __future__ import annotations

from django.http import HttpRequest, HttpResponse

from hyper.templates.profile_card.page import ProfileCardTemplate
from hyperdjango.shortcuts import render_template_block


def profile_card_name(request: HttpRequest) -> HttpResponse:
    return render_template_block(
        request,
        ProfileCardTemplate,
        "name_only",
        context={"name": "Waseem", "role": "Engineer"},
    )
```
