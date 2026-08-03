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
python manage.py hyper_scaffold
```

See the **[Installation guide](docs/reference/django-integration.md)** for details.

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
