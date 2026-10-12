# HyperDjango

[![PyPI version](https://img.shields.io/pypi/v/hyperdjango.svg)](https://pypi.org/project/hyperdjango/)
[![Downloads](https://img.shields.io/pypi/dm/hyperdjango.svg)](https://pypi.org/project/hyperdjango/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

*Built by [Charing Cross Capital](https://charingcrosscapital.com)*

Build interactive Django apps without splitting your product into "backend API + SPA frontend".

HyperDjango keeps rendering and business logic on the server, then layers in partial swaps, signals, and transitions for SPA-like UX.

## Documentation & Examples

For full API reference, guides, and interactive examples, please visit [hyperdjango.charingcrosscapital.com](https://hyperdjango.charingcrosscapital.com).

## Why This Works

- Keep business logic in Django, not duplicated across REST + frontend app layers.
- Get SPA-like interactions (partial swaps, toasts, transitions) with HTML as the transport.
- Organize by feature using file-based routes and co-located templates/assets in a `hyper/` directory.

## Quick Start

```bash
pip install hyperdjango
python manage.py hyper_scaffold --agent-skill
npm install
python manage.py hyper_runserver
```

The scaffold mounts HyperDjango, creates the `hyper/` frontend tree, configures
Vite, and installs the repository-local AI skill.

For rendered pages, create a route package instead of adding a `TemplateView`
to `urls.py`:

```text
hyper/routes/about/
├── +page.py
├── index.html
└── entry.ts       # optional; automatically loaded for this page
```

```python
# hyper/routes/about/+page.py
from django.http import HttpRequest

from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request: HttpRequest) -> dict[str, str]:
        return {"title": "About"}
```

```django
{# hyper/routes/about/index.html #}
<h1>{{ title }}</h1>
```

The page is available at `/about/`. A neighboring `entry.ts` or `entry.js` is
discovered and injected automatically; do not add a manual `<script>` tag.
Use `@action` and typed action results for interaction-level server updates.
APIs, webhooks, admin routes, and other non-page endpoints can continue using
ordinary Django or Django REST Framework routing.

See the [Getting Started guide](https://hyperdjango.charingcrosscapital.com/docs/getting-started)
and [AI Quickstart](https://hyperdjango.charingcrosscapital.com/docs/ai-quickstart).

## Install the AI Skill

HyperDjango ships an [Agent Skills](https://agentskills.io/) compatible skill.
Install it in the current repository with one command:

```bash
curl -fsSL --create-dirs -o .agents/skills/hyperdjango/SKILL.md https://raw.githubusercontent.com/charingcrosscapital/hyperdjango/main/hyperdjango/skills/hyperdjango/SKILL.md
```

Codex discovers repository skills from `.agents/skills`. Other agents may use a
client-specific skill directory; see the
[AI Quickstart](https://hyperdjango.charingcrosscapital.com/docs/ai-quickstart)
for alternatives. When scaffolding a project, `--agent-skill` performs the
repository-local installation without downloading another copy.

## Example App

A full runnable demo lives in `example/`. See [example/README.md](example/README.md) for instructions.

## Contributing

We welcome contributions. HyperDjango requires Python 3.13 or later. The project
uses a PEP 735 `dev` dependency group (currently containing the test tools), not
a `dev` optional extra, so `pip install -e .[dev]` is not valid.

Clone the repository and enter it:

```bash
git clone https://github.com/charingcrosscapital/hyperdjango.git
cd hyperdjango
```

### With uv (recommended)

`uv` reads the committed lockfile and installs the project plus its development
dependency group:

```bash
uv sync --group dev
uv run pytest
```

### Browser integration tests

The end-to-end runtime suite uses the example project and requires Node.js 20
or later. Install its dependencies and Chromium, then run it from `example/`:

```bash
cd example
npm ci
npx playwright install chromium
npm run test:browser
```

### With pip

Create a virtual environment, update to pip 25.1 or later, and install the
editable project with its `dev` dependency group:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e . --group dev
pytest
```

Open a pull request with your changes and tests that cover them.


## License

This project is licensed under the [MIT License](LICENSE).
