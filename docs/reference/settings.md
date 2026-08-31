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

- provides a fallback Vite dev server URL when development assets are used
  without `hyper_runserver`

Default:

```python
"http://localhost:5173/"
```

`python manage.py hyper_runserver` discovers Vite's actual URL and makes it
authoritative at runtime, including when Vite selects a different free port.
An explicit `HYPER_VITE_DEV_SERVER_URL` environment variable also takes
precedence over the Django setting.

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

### Inspector access-log filter

Inspector endpoint requests originate from Django's `django.server` logger. They
remain visible by default: HyperDjango does not mutate Django's global `LOGGING`
setting or install a process-wide filter. Projects that do not want those internal
HTTP access-log lines can opt in with this complete Django logging configuration:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "skip_hyperdjango_request_inspector": {
            "()": "hyperdjango.integrations.devtools.logging.RequestInspectorAccessLogFilter",
        },
    },
    "formatters": {
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
            "filters": ["skip_hyperdjango_request_inspector"],
        },
    },
    "loggers": {
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
```

For an existing `LOGGING` dictionary, merge the filter definition into `filters` and
add `"skip_hyperdjango_request_inspector"` to the `filters` list on the handler used by
`django.server`.

`RequestInspectorAccessLogFilter` normalizes
`HYPER_DEBUG_TOOLBAR_CONFIG["URL_PREFIX"]` before comparing it with the request path:
the default `"__hyperdebug__"` setting matches `/__hyperdebug__/` and its descendants,
and custom prefixes work the same way. It reads `record.request.path_info`, falling
back safely to `record.request.path`. Only matching records are suppressed. Records
without an attached request and ordinary page or action paths remain visible. The
filter belongs on the handler because changing the name of an already-created
`django.server` record would not re-route it through another logger.

## `HYPER_SWITCH_ACTION_MAX_DEPTH`

Type: `int`. Default: `4`.

Maximum accepted `SwitchAction` depth. Requests beyond the limit receive a structured
409 action error. Keep this aligned with the client runtime's `switchActionMaxDepth`
configuration. Increase it only for an intentional longer command/query chain.

## `HYPER_SSE_HEARTBEAT_INTERVAL`

Type: `int | float`. Default: `15`.

Number of idle seconds between SSE heartbeat comments for generator action streams.
HyperDjango emits `: heartbeat` when a sync or async generator has not produced an
action item during this interval. The comment keeps otherwise silent connections active
through proxies and is ignored by the browser runtime: it does not dispatch an event,
change the latest checkpoint, or reset the client's reconnect-attempt count.

Choose an interval shorter than the smallest idle timeout in the reverse-proxy, CDN, and
application-server path. Set the value to `0` to disable server heartbeats. One-shot
actions and already-active streams do not emit unnecessary heartbeat frames.

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
