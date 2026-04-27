# HyperDjango

[![PyPI version](https://img.shields.io/pypi/v/hyperdjango.svg)](https://pypi.org/project/hyperdjango/)
[![Downloads](https://img.shields.io/pypi/dm/hyperdjango.svg)](https://pypi.org/project/hyperdjango/)
[![License](https://img.shields.io/pypi/l/hyperdjango.svg)](https://pypi.org/project/hyperdjango/)

Build interactive Django apps without splitting your product into "backend API + SPA frontend".

HyperDjango keeps rendering and business logic on the server, then layers in partial swaps, signals, and transitions for SPA-like UX.

## Documentation

For full API reference and guides, please visit our **[official documentation](docs/reference/index.md)**.

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

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to set up the development environment, run tests, and submit pull requests.

## License

This project is licensed under the [MIT License](LICENSE).


