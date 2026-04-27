# HyperDjango

[![PyPI version](https://img.shields.io/pypi/v/hyperdjango.svg)](https://pypi.org/project/hyperdjango/)
[![Downloads](https://img.shields.io/pypi/dm/hyperdjango.svg)](https://pypi.org/project/hyperdjango/)
[![License](https://img.shields.io/pypi/l/hyperdjango.svg)](https://pypi.org/project/hyperdjango/)

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

We welcome contributions! To get started:

1.  **Clone the repository**: `git clone https://github.com/charingcrosscapital/hyperdjango.git`
2.  **Install dependencies**: `pip install -e .[dev]` (or equivalent)
3.  **Run tests**: `pytest`
4.  **Submit Pull Request**: Open a PR with your changes, ensuring new tests cover your modifications.


## License

This project is licensed under the [MIT License](LICENSE).


