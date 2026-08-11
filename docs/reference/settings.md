# Settings

## `HYPER_FRONTEND_DIR`

Type:

- `Path | str`

Purpose:

- tells HyperDjango where your `hyper/` directory lives

Expected contents usually include:

- `routes/`
- `layouts/`
- `templates/`
- shared frontend files

Example:

```python
HYPER_FRONTEND_DIR = BASE_DIR / "hyper"
```

## `HYPER_VITE_OUTPUT_DIR`

Type:

- `Path | str`

Purpose:

- tells HyperDjango where Vite writes built assets

Example:

```python
HYPER_VITE_OUTPUT_DIR = BASE_DIR / "dist"
```

## `HYPER_VITE_DEV_SERVER_URL`

Type:

- `str`

Purpose:

- tells HyperDjango which Vite dev server URL to inject during development

Example:

```python
HYPER_VITE_DEV_SERVER_URL = "http://localhost:5173/"
```

`python manage.py hyper_runserver` overrides this value at runtime with the
automatically assigned Vite URL. An explicit `HYPER_VITE_DEV_SERVER_URL`
environment variable also takes precedence over the setting.

## `HYPER_VITE_COMMAND`

Type:

- `str | list[str] | tuple[str, ...]`

Purpose:

- customizes the command used by `hyper_runserver` to start Vite

When omitted, HyperDjango detects Bun, pnpm, Yarn, or npm from its lockfile and
runs that package manager's `dev` script. HyperDjango appends Vite's host,
optional fixed port, and terminal options. Setting `HYPER_VITE_COMMAND`
explicitly bypasses package-manager and `node_modules` detection.

## Development diagnostics

Django's system-check framework validates HyperDjango configuration at startup:

- frontend directory availability and route compilation
- broken colocated Vite entry links
- presence of a Vite configuration during development
- production manifest presence and staleness

Each diagnostic includes a stable `hyperdjango.*` identifier and an actionable
hint.

## `HYPER_DEBUG_TOOLBAR`

Type:

- `bool`

Default:

- `False`

Purpose:

- explicitly enables HyperDjango's standalone request inspector when its app,
  middleware, and URLs are configured

`HYPER_DEBUG_TOOLBAR` is authoritative and does not implicitly follow Django's
`DEBUG` setting. Enabling it only inside `if DEBUG:` is the recommended local
development convention, but applications may choose a different environment or
access policy. Because the inspector exposes sanitized request traces and mutation
controls, review access and retention before enabling it on a public application.

## `HYPER_DEBUG_TOOLBAR_CONFIG`

Type:

- `dict[str, object]`

Supported keys:

- `MAX_HISTORY`: maximum number of unpinned in-process traces retained; defaults to `50`
- `URL_PREFIX`: URL prefix used to exclude inspector endpoints from tracing; defaults
  to `"__hyperdebug__"` and must match the prefix mounted in the URL configuration
- `RECORD_PAGE_REQUESTS`: whether to retain ordinary non-action requests; defaults to
  `True`. Set it to `False` to keep only requests carrying a Hyper action header or
  POST `_action` field while continuing to inject the inspector into HTML pages.

Example:

```python
HYPER_DEBUG_TOOLBAR_CONFIG = {
    "MAX_HISTORY": 75,
    "URL_PREFIX": "__hyperdebug__",
    "RECORD_PAGE_REQUESTS": False,
}
```

## `HYPER_SWITCH_ACTION_MAX_DEPTH`

Type: `int`. Default: `4`.

Maximum accepted `SwitchAction` depth. Requests beyond the limit receive a structured
409 action error. Keep this aligned with the client runtime's `switchActionMaxDepth`
configuration. Increase it only for an intentional longer command/query chain.

## `HYPER_DEV`

Type:

- `bool`

Purpose:

- switches asset loading between development mode and manifest-based production mode

Typical usage:

```python
HYPER_DEV = DEBUG
```

Behavior:

- `True`: use Vite dev server URLs and inject `@vite/client`
- `False`: resolve assets from the built Vite manifest in `HYPER_VITE_OUTPUT_DIR`
