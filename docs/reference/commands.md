# Commands

## `python manage.py hyper_runserver`

Purpose:

- start Django and Vite together for local development
- automatically select a free Vite port and make its URL available to HyperDjango

Useful flags:

- `--vite-port 5173` to request a fixed Vite port
- `--vite-host 127.0.0.1` to override Vite's bind host
- `--vite-public-host devbox.local` to set the hostname injected into browser URLs
- `--vite-timeout 15` to control the readiness deadline
- `--package-manager npm|pnpm|yarn|bun` to override lockfile detection
- `--auto-port` to select an available Django port too
- `--open` to open the app after Django begins accepting connections
- `--verbose` to include Vite startup details
- `--no-vite` to run only Django

All normal Django `runserver` arguments remain available. For example:

```bash
python manage.py hyper_runserver 8010
python manage.py hyper_runserver 0.0.0.0:8000
```

By default, Vite uses the same bind host as Django. Thus the second example
binds both Django and Vite to all IPv4 interfaces. For wildcard bind addresses,
HyperDjango injects `localhost` as the browser-facing Vite hostname.

For another device or a container-facing hostname, keep the wildcard bind and
provide the reachable hostname separately:

```bash
python manage.py hyper_runserver 0.0.0.0:8000 --vite-public-host devbox.local
```

The HyperDjango supervisor and Vite process stay alive across Django
autoreloads and stop together when the development server exits. Reload
children use Django's standard `runserver` entry point, so a temporary package
replacement cannot make the reload fail merely because its
`hyper_runserver` command module is briefly undiscoverable. Vite's terminal
clearing is disabled so its output does not replace Django's logs, and its
messages are merged into the command's output with a `[vite]` prefix. Django
startup messages use a `[django]` prefix, and a compact banner lists local and
network URLs.

HyperDjango detects Bun, pnpm, Yarn, or npm from the project's lockfile. It
prints the exact install command when `node_modules` is absent. An explicit
`HYPER_VITE_COMMAND` string or sequence disables package-manager detection.

Vite must report readiness before Django starts. Automatic Vite ports use
Vite's own collision handling, while fixed ports use `--strictPort`. Startup
errors include recent Vite output, unexpected Vite exits stop Django, and the
entire npm/Vite process group is terminated on shutdown.

When the HyperDjango development toolbar is active, request logs include total
duration, action name, SQL count/time, template-render time, and a direct trace
URL. Django 500 responses from HyperDjango requests are also presented using
Vite's browser error overlay.

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
