# Commands

## `python manage.py hyper_scaffold`

Purpose:

- generate a starter HyperDjango project structure

Useful flags:

- `--no-wire`
- `--force`

Argument details:

- `--no-wire`
  Do not patch Django settings or urls automatically
- `--force`
  Overwrite existing scaffolded files

Behavior:

- creates starter `hyper/routes`, `hyper/layouts`, and `hyper/templates` files
- creates or updates `vite.config.js`
- creates or updates `package.json`
- optionally patches Django settings and urls unless `--no-wire` is used

Generated layout starter:

- `hyper/layouts/base/__init__.py`
- `hyper/layouts/base/index.html`
- `hyper/layouts/base/entry.ts`

## `python manage.py hyper_routes`

Purpose:

- print compiled routes for inspection

Useful flags:

- `--json`

Argument details:

- `--prefix`
  Compile routes as if they were mounted under a URL prefix
- `--dir`
  Override the routes directory path
- `--json`
  Print route metadata as JSON instead of human-readable lines

Behavior:

- compiles the current route tree
- prints route paths and names
- useful in CI to catch route conflicts early
