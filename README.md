# HyperDjango

[![PyPI version](https://img.shields.io/pypi/v/hyperdjango.svg)](https://pypi.org/project/hyperdjango/)
[![Python versions](https://img.shields.io/pypi/pyversions/hyperdjango.svg)](https://pypi.org/project/hyperdjango/)
[![Django 4.2+](https://img.shields.io/badge/Django-4.2%2B-0C4B33?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Downloads](https://img.shields.io/pypi/dm/hyperdjango.svg)](https://pypi.org/project/hyperdjango/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/devwaseem/hyperdjango/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-online-blue.svg)](https://hyperdjango.charingcrosscapital.com/docs)

**Server-rendered Django with SPA-grade interactions, without splitting your product into a backend API and a JavaScript application.**

HyperDjango gives Django file-based page routing, co-located Vite assets, reusable layouts, typed server actions, streaming updates, Alpine integration, and production asset resolution. Your server remains the source of truth for business logic and HTML; the browser applies focused updates instead of rebuilding the application state model a second time.

Built by [Charing Cross Capital](https://charingcrosscapital.com).

- [Why HyperDjango](#why-hyperdjango)
- [Features](#features)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Core concepts](#core-concepts)
- [Add HyperDjango manually](#add-hyperdjango-manually)
- [Development commands](#development-commands)
- [Production](#production)
- [AI coding assistants](#ai-coding-assistants)
- [Documentation](#documentation)
- [Contributing](#contributing)

## Why HyperDjango

A conventional Django application renders HTML well, but rich interactions often grow into ad hoc JSON endpoints and browser state. A conventional SPA solves that by introducing a separate frontend application, API schema, router, state model, validation layer, and deployment surface.

HyperDjango takes a third path:

```text
request
  -> file route
  -> PageView
  -> adjacent Django template
  -> HTML document

interaction
  -> @action on the same page
  -> typed result or stream
  -> targeted HTML / signal / event / toast / history update
```

Use HyperDjango when:

- Django already owns your data, authorization, validation, and templates.
- You want partial updates, optimistic-feeling interactions, streaming, and navigation continuity without maintaining an SPA.
- You prefer feature-oriented packages where route, template, Python behavior, JavaScript, and CSS live together.
- You want progressive enhancement and server-rendered pages to remain the default architecture.

Use ordinary Django or Django REST Framework routes when the endpoint is an API, webhook, admin view, health check, or another non-page interface. HyperDjango complements Django; it does not require every endpoint to become a HyperDjango page.

## Features

- **File-based Django routing** — route directories compile into ordinary Django URL patterns, including typed, regex, grouped, composite, and catch-all segments.
- **Django-native page classes** — `HyperView` builds on Django's class-based view model and can return context dictionaries, template responses, redirects, streams, or ordinary `HttpResponse` objects.
- **Explicit reusable layouts** — share template shells, Python helpers, context, JavaScript, and CSS through layout packages and normal Python inheritance.
- **Automatic Vite entry discovery** — nearby `entry.ts`, `entry.js`, head entries, CSS imports, and module preloads are injected for pages, layouts, and template packages.
- **Typed server actions** — return HTML patches, deletes, events, toasts, history updates, redirects, JavaScript loads, and Alpine signal changes from page methods.
- **Streaming interactions** — yield action items over Server-Sent Events for progress, long-running work, and resumable read streams.
- **Alpine and vanilla JavaScript clients** — invoke actions with Alpine's `$action(...)` or `window.action(...)`.
- **Integrated development server** — one command supervises Django and Vite, discovers free ports, preserves autoreload, and surfaces startup failures.
- **Route and request diagnostics** — inspect compiled routes and optionally enable the development request inspector for actions, rendering, SQL, timings, exceptions, and completed streams.
- **Manifest-based production assets** — resolve hashed builds from a private Vite manifest while publishing only browser-safe static assets.

## Requirements

- Python 3.13 or later
- Django 4.2 or later
- Node.js 20.19 or later when developing or building Vite assets
- A Django project with staticfiles configured for production deployment

## Quick start

The following path starts from an existing Django project. If you need one first:

```bash
python -m pip install Django
python -m django startproject config .
```

### 1. Install HyperDjango

```bash
python -m pip install hyperdjango
```

Add the application before running its management commands:

```python
# config/settings.py
INSTALLED_APPS = [
    # Django and project applications...
    "hyperdjango",
]
```

### 2. Scaffold the HyperDjango project files

```bash
python manage.py hyper_scaffold --agent-skill
```

The scaffolder:

- creates starter routes, a base layout, and a reusable template package;
- creates or updates `vite.config.js` and `package.json`;
- wires the HyperDjango settings and `include_routes()` into the active Django project;
- installs the repository-local AI skill when `--agent-skill` is present;
- preserves existing scaffolded files unless `--force` is explicitly supplied.

The generated structure is organized by frontend ownership:

```text
.
├── hyper/
│   ├── layouts/
│   │   └── base/
│   │       ├── __init__.py
│   │       ├── index.html
│   │       └── entry.ts
│   ├── routes/
│   │   └── index/
│   │       ├── +page.py
│   │       └── index.html
│   ├── shared/
│   └── templates/
│       └── profile_card/
│           ├── page.py
│           └── index.html
├── vite.config.js
└── package.json
```

Use `--no-wire` when you want to create the files but edit Django settings and URLs yourself.

### 3. Install frontend dependencies and run both servers

```bash
npm install
python manage.py hyper_runserver --open
```

`hyper_runserver` starts Vite first, waits for it to become ready, exposes its actual runtime URL to HyperDjango, and then starts Django. If port 8000 is occupied, the command chooses the next available port.

### 4. Add a rendered page

Create `hyper/routes/about/+page.py`:

```python
from django.http import HttpRequest

from hyper.layouts.base import BaseLayout


class PageView(BaseLayout):
    def get(self, request: HttpRequest) -> dict[str, str]:
        return {
            "title": "About",
            "body": "This page is routed and rendered by HyperDjango.",
        }
```

Create the adjacent template at `hyper/routes/about/index.html`:

```django
{% extends "layouts/base/index.html" %}

{% block page %}
  <article>
    <h1>{{ title }}</h1>
    <p>{{ body }}</p>
  </article>
{% endblock page %}
```

The page is now available at `/about/`. There is no matching entry to add to the root `urlpatterns`; `include_routes()` compiles it from the filesystem.

### 5. Add page-local TypeScript and CSS

Create `hyper/routes/about/entry.ts`:

```ts
import "./about.css";

console.log("About page loaded");
```

Create `hyper/routes/about/about.css`:

```css
article {
  max-width: 70ch;
  margin-inline: auto;
}
```

HyperDjango and Vite discover the entry, include its imported CSS, and load it only when the page needs it. Do not add a manual `<script>` or `<link>` tag for a discovered entry.

### 6. Add a server interaction

The scaffolded base layout initializes Alpine. Add an action to the page:

```python
from django.http import HttpRequest

from hyperdjango.actions import action
from hyperdjango.integrations.alpine.actions import Signal
from hyper.layouts.base import BaseLayout


class PageView(BaseLayout):
    def get(self, request: HttpRequest) -> dict[str, str]:
        return {"title": "Counter"}

    @action
    def increment(self, request: HttpRequest, count: int = 0):
        return [Signal(name="count", value=count + 1)]
```

Invoke it from the adjacent template:

```django
{% extends "layouts/base/index.html" %}

{% block page %}
  <section x-data="{ count: 0 }">
    <h1>{{ title }}</h1>
    <p>Count: <span x-text="count"></span></p>
    <button type="button" @click="$action('increment', { count })">
      Increment
    </button>
  </section>
{% endblock page %}
```

The request is dispatched to `PageView.increment()`. The returned `Signal` updates the local Alpine state without a page navigation or a custom JSON API.

## Core concepts

### File-based routes

HyperDjango scans `hyper/routes/` for `+page.py`. Every page module defines a class named `PageView`.

| Filesystem route | URL behavior |
| --- | --- |
| `hyper/routes/index/+page.py` | `/` |
| `hyper/routes/about/+page.py` | `/about/` |
| `hyper/routes/blog/[slug]/+page.py` | `/blog/<slug>/` |
| `hyper/routes/users/[int__id]/+page.py` | `/users/<int:id>/` |
| `hyper/routes/(marketing)/pricing/+page.py` | `/pricing/`; group omitted from the URL |
| `hyper/routes/docs/[...path]/+page.py` | catch-all path beneath `/docs/` |
| `hyper/routes/invites/[code__[A-Z0-9]{8}]/+page.py` | inline regex segment |
| `hyper/routes/reset/[uidb36]-[key]/+page.py` | multiple captures in one URL segment |

Nested directories create nested URLs. HyperDjango generates Django route names automatically, supports mounting the whole tree under a prefix, and rejects ambiguous route shapes during compilation.

Inspect the compiled result locally and in CI:

```bash
python manage.py hyper_routes
python manage.py hyper_routes --json
```

A file route can also expose a plain Django `View` when you want filesystem routing without the `HyperView` rendering or action APIs.

[Read the routing guide](https://hyperdjango.charingcrosscapital.com/docs/routing).

### Pages and rendering

For a conventional page, `HyperView.get()` returns a context dictionary and HyperDjango renders the adjacent `index.html`. Page methods can also use rendering helpers for full templates, reusable template packages, or named blocks.

A `HyperView` may return normal Django responses when that is the clearer contract. Authentication, permissions, middleware, forms, ORM operations, transactions, caching, and the rest of Django continue to work normally.

[Read the pages and rendering guide](https://hyperdjango.charingcrosscapital.com/docs/pages-and-rendering).

### Layouts

Layouts live under `hyper/layouts/`. A layout package can own:

- a Django template shell;
- a Python base class and shared helpers;
- shared context through `get_context()`;
- `entry.ts`, `entry.js`, or head entries;
- CSS imported from those entries.

Pages opt into a layout explicitly by inheriting its class and extending its template. This keeps layout behavior visible in ordinary Python and Django template relationships instead of relying on hidden directory inheritance.

[Read the layouts guide](https://hyperdjango.charingcrosscapital.com/docs/layouts).

### Co-located assets and Vite

HyperDjango discovers these files beside routed pages, layouts, and standalone template packages:

| Entry | Placement |
| --- | --- |
| `entry.ts` / `entry.js` | body module |
| `entry.head.ts` / `entry.head.js` | document head module |
| `*.entry.ts` / `*.entry.js` | custom named entry |
| CSS imported by an entry | stylesheet resolved by Vite |

Put code at the narrowest ownership boundary. Page-only behavior belongs beside the page; shared behavior belongs in the layout or template package that owns it.

In development, HyperDjango loads entries from the Vite server. In production, it resolves hashed files, imported CSS, and module preloads from `dist/.vite/manifest.json`.

[Read the assets and Vite guide](https://hyperdjango.charingcrosscapital.com/docs/assets-and-vite).

### Actions

Actions are methods marked with `@action`. Use page handlers such as `get()` and `post()` for full-page rendering, and actions for interaction-level changes.

An action signature is a strict request contract. HyperDjango supplies every parameter captured by the current file route, plus every key sent through `X-Hyper-Data`, query parameters, or a non-GET form. Route values override request values with the same name.

For example, an action under `payment-runs/[run_id]/[segment_code]/review/+page.py` invoked with `{ decision }` must accept `run_id`, `segment_code`, and `decision` after `request`. Missing or unexpected names produce an actionable `400` response before the method is called; HyperDjango never silently drops input. Use `**params` only for intentionally open-ended payloads because it also accepts misspellings.

```python
from hyperdjango.actions import HTML, Toast, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def create(self, request):
        return [
            HTML(content="<li>New item</li>", target="#todo-list", swap="append"),
            Toast(payload={"type": "success", "message": "Created"}),
        ]
```

Typed results can:

- patch or delete HTML;
- change Alpine signals;
- dispatch browser events;
- show toasts;
- update browser history;
- redirect or load JavaScript.

Return a list or tuple when the complete result is immediately available. Yield items from a generator when updates genuinely arrive over time:

```python
class PageView(HyperView):
    @action
    def run_job(self, request):
        yield HTML(content="<p id='status'>Starting…</p>", target="#status")
        yield HTML(content="<p id='status'>Complete</p>", target="#status")
```

Invoke actions with Alpine:

```html
<button @click="$action('search', { q }, { sync: 'replace', key: 'search' })">
  Search
</button>
```

Or with plain JavaScript:

```js
window.action("search", { q }, { sync: "replace", key: "search" });
```

[Read the actions guide](https://hyperdjango.charingcrosscapital.com/docs/actions) and [client-side action guide](https://hyperdjango.charingcrosscapital.com/docs/client-side-actions).

## Add HyperDjango manually

If you do not use `hyper_scaffold`, configure the integration directly.

### Settings

```python
# config/settings.py
INSTALLED_APPS = [
    # ...
    "hyperdjango",
]

HYPER_FRONTEND_DIR = BASE_DIR / "hyper"
HYPER_VITE_OUTPUT_DIR = BASE_DIR / "dist"
HYPER_DEV = DEBUG

TEMPLATES[0]["DIRS"].append(HYPER_FRONTEND_DIR)

HYPER_VITE_ASSETS_DIR = HYPER_VITE_OUTPUT_DIR / "assets"
STATICFILES_DIRS = (
    [("assets", HYPER_VITE_ASSETS_DIR)]
    if HYPER_VITE_ASSETS_DIR.exists()
    else []
)
```

`HYPER_VITE_DEV_SERVER_URL` is optional. `hyper_runserver` supplies the authoritative runtime URL automatically; configure a fallback URL only when another process starts Vite.

### URLs

```python
# config/urls.py
from django.contrib import admin
from django.urls import path

from hyperdjango.urls import include_routes

urlpatterns = [
    path("admin/", admin.site.urls),
    *include_routes(),
]
```

Mount the generated routes under a prefix when needed:

```python
urlpatterns = [
    *include_routes(url_prefix="app"),
]
```

You still need a Vite configuration that discovers the entries under `hyper/`. The generated `vite.config.js` is the recommended starting point; run `python manage.py hyper_scaffold --no-wire` if you only want HyperDjango's project files.

## Development commands

| Command | Purpose |
| --- | --- |
| `python manage.py hyper_scaffold` | Create the starter `hyper/` tree and Vite configuration; wire Django unless `--no-wire` is used. |
| `python manage.py hyper_scaffold --agent-skill` | Scaffold and install the bundled repository-local AI skill. |
| `python manage.py hyper_scaffold --force` | Replace files owned by the scaffold. Review project-specific changes before using it. |
| `python manage.py hyper_runserver` | Run Django and Vite under one supervisor with automatic port discovery. |
| `python manage.py hyper_runserver --open` | Start the development stack and open the application. |
| `python manage.py hyper_runserver --no-vite` | Run only Django while preserving normal `runserver` arguments. |
| `python manage.py hyper_routes` | Compile and print file routes; fail on route conflicts. |
| `python manage.py hyper_routes --json` | Emit route metadata for tooling or CI. |
| `npm run build` | Produce the Vite manifest and hashed production assets. |

`hyper_runserver` detects npm, pnpm, Yarn, or Bun from the project's lockfile. Standard Django `runserver` addresses and options remain available.

[Read the command reference](https://hyperdjango.charingcrosscapital.com/docs/reference/commands).

## Production

A production deployment serves Django normally and uses Vite's built manifest rather than a development server.

1. Build frontend assets before collecting static files:

   ```bash
   npm run build
   python manage.py collectstatic --noinput
   ```

2. Configure production settings:

   ```python
   HYPER_DEV = False
   HYPER_FRONTEND_DIR = BASE_DIR / "hyper"
   HYPER_VITE_OUTPUT_DIR = BASE_DIR / "dist"
   STATICFILES_DIRS = [("assets", HYPER_VITE_OUTPUT_DIR / "assets")]
   ```

3. Publish `dist/assets/` through Django staticfiles or your static asset service. Keep `dist/.vite/manifest.json` server-side; it contains source-relative lookup keys and should not be exposed as a public static file.
4. Use hashed entry, chunk, and asset filenames. The scaffolded Vite configuration already follows this pattern.
5. Run deployment checks and route compilation:

   ```bash
   python manage.py check --deploy
   python manage.py hyper_routes
   ```

Keep Django CSRF protection enabled. Do not let proxies or CDNs cache action responses, and disable or access-protect the development request inspector in production.

[Review the production checklist](https://hyperdjango.charingcrosscapital.com/docs/production-checklist) before deploying.

## AI coding assistants

HyperDjango ships an [Agent Skills](https://agentskills.io/) compatible skill that teaches coding agents the route, asset, layout, and action conventions.

The recommended installation is part of scaffolding:

```bash
python manage.py hyper_scaffold --agent-skill
```

Install or update the latest skill directly in an existing repository:

```bash
curl -fsSL --create-dirs -o .agents/skills/hyperdjango/SKILL.md https://raw.githubusercontent.com/devwaseem/hyperdjango/main/hyperdjango/skills/hyperdjango/SKILL.md
```

Codex discovers repository skills in `.agents/skills`. Claude Code uses `.claude/skills`; replace `.agents` in the output path for that client. Other Agent Skills-compatible tools may use another discovery directory while retaining the required `hyperdjango/SKILL.md` shape.

[Read the AI quickstart](https://github.com/devwaseem/hyperdjango/blob/main/docs/ai-quickstart.md).

## Documentation

The README is intended to take a project from installation through its first real page, asset, and interaction. The documentation goes deeper into individual contracts:

- [Getting started](https://hyperdjango.charingcrosscapital.com/docs/getting-started)
- [AI quickstart](https://github.com/devwaseem/hyperdjango/blob/main/docs/ai-quickstart.md)
- [Routing](https://hyperdjango.charingcrosscapital.com/docs/routing)
- [Pages and rendering](https://hyperdjango.charingcrosscapital.com/docs/pages-and-rendering)
- [Layouts](https://hyperdjango.charingcrosscapital.com/docs/layouts)
- [Base template](https://hyperdjango.charingcrosscapital.com/docs/base-template)
- [Actions](https://hyperdjango.charingcrosscapital.com/docs/actions)
- [Client-side actions](https://hyperdjango.charingcrosscapital.com/docs/client-side-actions)
- [Declarative HTML APIs](https://hyperdjango.charingcrosscapital.com/docs/declarative-html-apis)
- [Alpine integration](https://hyperdjango.charingcrosscapital.com/docs/alpine-integration)
- [Assets and Vite](https://hyperdjango.charingcrosscapital.com/docs/assets-and-vite)
- [Development request inspector](https://hyperdjango.charingcrosscapital.com/docs/dev-toolbar)
- [Troubleshooting](https://hyperdjango.charingcrosscapital.com/docs/troubleshooting)
- [Production checklist](https://hyperdjango.charingcrosscapital.com/docs/production-checklist)
- [API reference](https://hyperdjango.charingcrosscapital.com/docs/reference)
- [Changelog](https://github.com/devwaseem/hyperdjango/blob/main/CHANGELOG.md)

AI-readable documentation is available at [`/llms.txt`](https://hyperdjango.charingcrosscapital.com/llms.txt).

## Example application

A runnable project covering routing, layouts, actions, streaming, assets, history, template packages, and diagnostics lives in [`example/`](https://github.com/devwaseem/hyperdjango/tree/main/example).

```bash
git clone https://github.com/devwaseem/hyperdjango.git
cd hyperdjango
uv sync --group dev

cd example
npm install
../.venv/bin/python manage.py hyper_runserver --open
```

## Contributing

HyperDjango requires Python 3.13 or later. Development dependencies use the PEP 735 `dev` dependency group rather than a `dev` optional extra.

```bash
git clone https://github.com/devwaseem/hyperdjango.git
cd hyperdjango
uv sync --group dev
uv run pytest
```

The browser integration suite uses the example project and Chromium:

```bash
cd example
npm ci
npx playwright install chromium
npm run test:browser
```

With pip 25.1 or later:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e . --group dev
pytest
```

Open an issue before substantial API changes so the behavior and migration path can be agreed upon. Pull requests should include focused tests for changed contracts and update the relevant guide or reference page.

## License

HyperDjango is released under the [MIT License](https://github.com/devwaseem/hyperdjango/blob/main/LICENSE).
