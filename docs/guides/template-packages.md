# Template Packages (`hyper/templates`)

Use `hyper/templates` when you want HyperDjango templating/assets without file-routed URLs.

This is useful for custom Django views where you still want:

- `PageTemplate` rendering helpers
- Vite entry discovery for co-located JS
- Hyper asset tags in templates

## Directory Pattern

```text
hyper/
  templates/
    profile_card/
      page.py
      index.html
      partials/
        body.html
      entry.ts
```

Anything under `hyper/templates` is not auto-mounted as a route.

## Define a Template Class

```python
from hyperdjango.page import PageTemplate


class ProfileCardTemplate(PageTemplate):
    pass
```

## Use It in a Custom Django View

```python
from django.http import HttpResponse
from hyper.templates.profile_card.page import ProfileCardTemplate


def profile_card(request):
    page = ProfileCardTemplate()
    html = page.render(
        request=request,
        context_updates={"title": "Account", "description": "Hello"},
    )
    return HttpResponse(html)
```

Or use shortcuts:

```python
from hyperdjango.shortcuts import render_template_page
from hyper.templates.profile_card.page import ProfileCardTemplate


def profile_card(request):
    return render_template_page(
        request,
        ProfileCardTemplate,
        context={"title": "Account", "description": "Hello"},
    )
```

## Rendering Blocks

```python
from hyperdjango.shortcuts import render_template_block


def profile_card_body(request):
    return render_template_block(
        request,
        ProfileCardTemplate,
        "card_body",
        context={"title": "Account"},
    )
```
