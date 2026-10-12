# AI Quickstart

HyperDjango uses conventions that general Django knowledge does not imply. Give this page or the bundled skill to a coding agent before it adds pages, frontend assets, layouts, or interactive behavior.

## Install the Agent Skill

From the root of a HyperDjango project, install the latest repository-local skill:

```bash
curl -fsSL --create-dirs -o .agents/skills/hyperdjango/SKILL.md https://raw.githubusercontent.com/devwaseem/hyperdjango/main/hyperdjango/skills/hyperdjango/SKILL.md
```

Codex discovers repository skills from `.agents/skills`. For Claude Code, replace `.agents` with `.claude`. Other Agent Skills-compatible clients may use another discovery directory; keep the required `hyperdjango/SKILL.md` directory shape.

When creating or updating the project with HyperDjango's scaffolder, install the bundled copy without a network request:

```bash
python manage.py hyper_scaffold --agent-skill
```

You can give an agent this instruction directly:

> Install the HyperDjango skill in this repository, read it, and follow it for every rendered page, route, layout, frontend entry, and server interaction you change.

## Default Decisions

| Task | Default |
| --- | --- |
| Add a rendered page | Create `hyper/routes/<route>/+page.py` and `index.html`. |
| Add a dynamic URL | Use a route directory such as `[slug]` or `[int__id]`. |
| Add page-local JavaScript or CSS | Add a neighboring `entry.ts` or `entry.js`; import CSS from it. |
| Add code shared by a layout subtree | Put the entry in the relevant layout package. |
| Add an interaction-level server update | Add an `@action` method returning typed action items. |
| Add an API, webhook, admin, or infrastructure endpoint | Ordinary Django or Django REST Framework routing can be the better fit. |

## Add a Page

For `/about/`, create:

```text
hyper/routes/about/
├── +page.py
├── index.html
└── entry.ts       # optional
```

`hyper/routes/about/+page.py`:

```python
from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request: HttpRequest) -> dict[str, str]:
        return {"title": "About"}
```

`hyper/routes/about/index.html`:

```django
<h1>{{ title }}</h1>
<p>This page was rendered by HyperDjango.</p>
```

HyperDjango discovers the `PageView` and exposes the page at `/about/`. Do not duplicate the page in the root Django `urlpatterns`.

See [Routing](routing.md) for nested, grouped, typed, regex, and catch-all routes.

## Add Frontend Code

Use co-located Vite entries:

- `entry.ts` or `entry.js` loads as a body module.
- `entry.head.ts` or `entry.head.js` loads in the document head.
- CSS imported by an entry is included automatically.
- Pages, layouts, and standalone template packages all support nearby entries.

Do not add a manual `<script>` tag for a discovered entry. Put code at the narrowest ownership boundary: page-only behavior belongs beside the page; shared behavior belongs in the relevant layout or template package.

See [Assets and Vite](assets-and-vite.md) for development and production behavior.

## Add an Interaction

Use full-page handlers such as `get()` and `post()` for page rendering. Use `@action` for interaction-level updates:

```python
from django.http import HttpRequest

from hyperdjango.actions import HTML, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def save(self, request: HttpRequest):
        return [HTML(content="<div id='flash'>Saved</div>", target="#flash")]
```

Prefer typed results such as `HTML`, `Delete`, `Signal`, `Signals`, `Toast`, `Event`, `History`, and `Redirect` over inventing a JSON endpoint and bespoke browser state protocol.

See [Actions](actions.md) and [Client-Side Actions](client-side-actions.md).

## Verify the Result

Compile routes before running the application:

```bash
python manage.py hyper_routes
```

Exercise the changed page through the actual development server:

```bash
python manage.py hyper_runserver
```

For production asset changes, run the project's Vite build and Django deployment checks. See the [Production Checklist](production-checklist.md).
