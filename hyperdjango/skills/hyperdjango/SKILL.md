---
name: hyperdjango
description: Builds and modifies HyperDjango applications with file-based page routes, HyperView pages and layouts, automatically discovered Vite entries, and typed server actions. Use when a Django project imports hyperdjango, contains a hyper/routes tree or +page.py files, or when adding HyperDjango pages, routes, templates, JavaScript, CSS, layouts, forms, or interactions.
license: MIT
metadata:
  author: Charing Cross Capital
  framework: hyperdjango
---

# HyperDjango

Use HyperDjango's conventions before falling back to generic Django page patterns.

## Classify the endpoint

- Rendered application page: use a HyperDjango file route.
- Interaction on a rendered page: use an `@action` on its page class.
- API, webhook, admin, health check, or infrastructure endpoint: ordinary Django or Django REST Framework routing may be the better fit.
- Preserve an established project convention when the existing application intentionally differs.

## Add a rendered page

Create a route package under `hyper/routes/`. A basic `/about/` page is:

```text
hyper/routes/about/
├── +page.py
├── index.html
└── entry.ts       # optional, page-local frontend entry
```

```python
from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request: HttpRequest) -> dict[str, str]:
        return {"title": "About"}
```

HyperDjango discovers `PageView`; do not duplicate this page in Django's root `urlpatterns`.

Route directories encode URL behavior:

- `index/+page.py` maps to the containing root.
- `about/+page.py` maps to `/about/`.
- `[slug]/+page.py` captures a string parameter.
- `[int__id]/+page.py` uses a Django converter.
- `(marketing)/pricing/+page.py` groups files without changing the URL.
- `[...path]/+page.py` captures the remaining path.

## Place frontend assets by ownership

Use a nearby `entry.ts` or `entry.js` for body code and `entry.head.ts` or `entry.head.js` only for code that must run in the document head. Import CSS from the entry.

HyperDjango discovers entries beside routed pages, layout packages, and standalone template packages and injects their scripts, styles, and module preloads. Do not add manual script tags for discovered entries.

Keep page-only behavior beside the page. Put shared behavior in the narrowest layout or template package that owns it.

## Add interactions with actions

Use page handlers such as `get()` and `post()` for full-page rendering. Use `@action` for interaction-level updates:

```python
from django.http import HttpRequest

from hyperdjango.actions import HTML, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def save(self, request: HttpRequest):
        return [HTML(content="<div id='flash'>Saved</div>", target="#flash")]
```

Build the signature from the actual invocation, not from page context. Every parameter captured by the current file route is injected into every action. HyperDjango also passes every key from `X-Hyper-Data`, then missing query and non-GET form keys; route values win on name collisions.

The action must accept every assembled name, and every required parameter must be supplied. Use defaults for optional inputs. Use `**params` only for an intentionally open-ended payload because it also accepts typos. Before finishing, trace each `$action(...)` or `window.action(...)` call to its method and verify exact name parity.

Prefer typed results such as `HTML`, `Delete`, `Signal`, `Signals`, `Toast`, `Event`, `History`, and `Redirect`. Use streaming generators only when results genuinely arrive over time. Avoid inventing a JSON endpoint and bespoke browser state protocol for an interaction that an action already models.

## Work in an existing project

1. Inspect the nearest route, layout, or template package and follow its imports, base class, and template structure.
2. Trace every client action invocation to its Python method; include current route parameters and supplied data, query, or form names in the signature.
3. Put new code at the narrowest ownership boundary.
4. Migrate every affected caller instead of retaining parallel generic-Django and HyperDjango page paths.
5. Run `python manage.py hyper_routes` to compile routes and catch conflicts.
6. Exercise the changed page through `python manage.py hyper_runserver`.
7. For production asset changes, run the project's Vite build and Django deployment checks.

## Read deeper only when needed

- AI quickstart: https://hyperdjango.charingcrosscapital.com/docs/ai-quickstart
- Routing: https://hyperdjango.charingcrosscapital.com/docs/routing
- Pages and rendering: https://hyperdjango.charingcrosscapital.com/docs/pages-and-rendering
- Layouts: https://hyperdjango.charingcrosscapital.com/docs/layouts
- Actions: https://hyperdjango.charingcrosscapital.com/docs/actions
- Client-side actions: https://hyperdjango.charingcrosscapital.com/docs/client-side-actions
- Assets and Vite: https://hyperdjango.charingcrosscapital.com/docs/assets-and-vite
- Full documentation index: https://hyperdjango.charingcrosscapital.com/llms.txt
