# HyperDjango Debug Toolbar

HyperDjango ships a standalone development toolbar designed specifically for file
routes, actions, partial rendering, and SSE streams. It has no dependency on Django
Debug Toolbar and does not require a separate package install.

The toolbar is intended for development and controlled demonstrations. It keeps a
bounded request history in process memory and injects its interface only into normal
HTML responses.

Trace snapshots and pin state live in the Django process; they are not written to a
database, cache, browser storage, or disk. A full browser refresh clears the process
store's unpinned traces before loading the new request tape. Pinned traces survive the
refresh, bounded-history eviction, and **Clear**, but all traces and pins disappear when
the Django process restarts.

## Enable it

Add the integration app and middleware only in development:

```python
# settings.py
if DEBUG:
    INSTALLED_APPS += ["hyperdjango.integrations.devtools"]

    MIDDLEWARE = [
        "hyperdjango.integrations.devtools.middleware.HyperDjangoDebugToolbarMiddleware",
        *MIDDLEWARE,
    ]

    HYPER_DEBUG_TOOLBAR = True
    HYPER_DEBUG_TOOLBAR_CONFIG = {
        "MAX_HISTORY": 50,
        "URL_PREFIX": "__hyperdebug__",
        "RECORD_PAGE_REQUESTS": True,
    }
```

Place the middleware near the start of the list so it surrounds HyperDjango dispatch.
If the project uses `GZipMiddleware`, place the debug middleware immediately after it
so HTML injection happens before compression.

Mount the private development endpoints before file routes:

```python
# urls.py
from django.conf import settings
from django.urls import include, path

from hyperdjango.urls import include_routes

urlpatterns = [
    *include_routes(),
]

if settings.DEBUG:
    urlpatterns = [
        path(
            "__hyperdebug__/",
            include("hyperdjango.integrations.devtools.urls"),
        ),
        *urlpatterns,
    ]
```

`URL_PREFIX` and the mounted URL prefix must match. Restart Django after changing the
app, middleware, or URL configuration.

To keep the request tape focused on HyperDjango actions, disable normal page-request
recording:

```python
HYPER_DEBUG_TOOLBAR_CONFIG = {
    "RECORD_PAGE_REQUESTS": False,
}
```

The middleware still injects the inspector launcher into eligible HTML pages, but it
does not create a trace for those page navigations. Requests carrying a Hyper action
through `X-Hyper-Action` or a POST `_action` field continue to be recorded, including
failed and streaming actions.

Inspector endpoints and URLs in Django Debug Toolbar's `djdt` namespace are always
excluded from capture and injection. This prevents DJDT history polling (for example,
`__debug__/history_sidebar/`) from recursively filling HyperDjango's request tape.

### Optionally hide inspector access logs

Django emits requests to the inspector's own endpoints through the `django.server`
logger, just like ordinary page and action requests. HyperDjango does not change
Django's global logging configuration or hide these requests by default. To suppress
only the inspector endpoint access logs, opt in by attaching
`RequestInspectorAccessLogFilter` to the `django.server` console handler:

```python
# settings.py
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

If the project already defines `LOGGING`, add the filter definition and its name to
the existing handler used by `django.server` instead of replacing unrelated logging
configuration.

The filter reads `HYPER_DEBUG_TOOLBAR_CONFIG["URL_PREFIX"]` and normalizes it as a
request path. The default setting, `"__hyperdebug__"`, therefore matches
`/__hyperdebug__/` and its descendants; a custom configured prefix is handled the same
way. It checks `record.request.path_info`, falling back safely to
`record.request.path`. Records without a request, and normal page or action requests
outside that prefix, continue to be logged. A handler filter is used because Django
has already created these records as `django.server`; changing a record's logger name
at that point would not route it through a different logger configuration.

### Enabling it independently of `DEBUG`

`HYPER_DEBUG_TOOLBAR` is the authoritative enablement switch. `DEBUG=True` is the
recommended convention for local development, but the inspector does not require it.
Consumers may enable it in any environment:

```python
HYPER_DEBUG_TOOLBAR = True
```

Register the integration app and middleware and mount its URLs under the same condition
used for that setting. The inspector exposes sanitized request traces and debugging
controls, so review access and data-retention requirements before enabling it on a
publicly accessible application.

## Open the inspector

Load a normal HyperDjango page. A compact **HYPERDJANGO** launcher appears
at the bottom-right. Select it or press <kbd>Control</kbd> + <kbd>Shift</kbd> +
<kbd>H</kbd>.

The inspector is divided into a request tape and a detail workspace:

- filter history by path, method, handler, or action
- select an earlier request without reloading the page
- keep inspecting the selected trace while newer traces append to the Request Tape;
  incoming traces never steal the detail view
- filter by all requests, actions, SSE responses, or errors
- pin or unpin an individual trace from the control on its Request Tape item so bounded-history eviction and **Clear** preserve it
- pause and resume capture, or clear all unpinned traces; a full page refresh performs
  the same pin-aware clear automatically
- replay a captured action after an explicit confirmation
- use **Locate** beside DOM targets, triggers, focus references, and observed nodes to
  close the drawer, scroll the exact element into view, and highlight it briefly; new
  traces retain a unique structural selector, while ambiguous legacy selectors are
  rejected instead of selecting the first class match
- use the contextual **Copy** icon beside request paths, source locations, exact DOM
  selectors, result/SSE content, SQL, and sanitized SQL parameters; the icon confirms
  success or failure in place and remains keyboard accessible
- keep the toolbar open or closed across page loads

The interface adapts to narrow and touch screens, exposes controls when the tab strip
overflows, uses a taller bottom-sheet drawer on phones and short landscape viewports,
replaces the desktop tab strip with a full-width section picker, and turns the request
tape and summary metrics into contained horizontal rails. Health and diagnostic rows
stack vertically instead of preserving desktop-only columns. The inspector uses a fixed
light canvas with high-contrast chrome and respects reduced-motion preferences.

The inspector uses eight task-oriented tabs: **Overview**, **Route**, **Action**,
**Output**, **Timeline**, **Database**, **Request / Response**,
and **Errors / Logs**. Related evidence is grouped in the tab where it answers the next
debugging question instead of being repeated across separate views.

When the site is started with `hyper_runserver`, each Django request log includes a
clickable trace URL plus request, action, SQL, and rendering timings. A failed
HyperDjango request with status 500 opens Vite's familiar browser error overlay using
the captured Python exception and source location; the full sanitized trace remains in
the **Errors / Logs** tab. This integration is active when `HYPER_DEBUG_TOOLBAR` is
true and the middleware and URLs are configured.

## What it records

### Overview

- HTTP status and complete middleware duration
- HyperDjango dispatch duration
- matched route identity, frontend-relative directory, and selected handler
- render, result-item, and exception counts
- response/SSE bytes, time to first byte, SQL time, log count, and rendering costs
- warnings for phases at least 100 ms, queries at least 50 ms, and responses at least
  500 KB
- contract and stream diagnostics, including error, warning, pass, and stream-event
  counts with the detailed findings directly below them

The Overview header uses the human route name and frontend-relative directory instead
of the generated dynamic Python class name.

### Route resolution

The **Route** tab connects the matched URL to its file-route implementation:

- route name, compiled pattern, namespace, parameters, and project-relative route directory
- `+page.py`, the resolved page template, and inherited layout classes with source links
- only the HTTP handler or Hyper action selected by this request, including its source
  and sync, async, or streaming mode
- route and layout Vite entry files, their head/body placement, and source links
- resolved module, preload, and stylesheet URLs
- whether each resolved asset is present or was requested by the current browser document
- route-specific source and template resolution diagnostics

Browser asset state describes the document currently hosting the inspector. Historical
traces retain their server-side route and resolved-asset metadata, but their browser
state may belong to a page that is no longer open.

### Action output

- action name, requested target, and merged arguments
- typed `HTML`, `Delete`, `Signal`, `Signals`, `Toast`, `Event`, `History`,
  `Redirect`, `Checkpoint`, `SwitchAction`, and `LoadJS` results
- target and swap behavior
- focus, transition, strict-target, swap-delay, and settle-delay options
- history/redirect URLs, event names, script sources, statuses, and headers
- sanitized signal values and event/toast payloads
- per-item sequence, event name, request-relative timestamp, gap, and payload bytes
- client-observed reconnect, cancellation, terminal-event, and target-outcome health
- command/query chain links with source and destination actions, separate request IDs,
  the client-derived retry decision, and switch depth; malformed handoffs and
  depth-limit failures appear in request diagnostics
- cross-endpoint destination route names and reversed URLs without exposing action data

The website's [live command-to-query demo](/#switch-action-demo) is an immediately
available trace source: running it creates linked command, destination, and reconnect
requests with separate IDs for inspection.

### Output and browser outcomes

Without modifying the Hyper runtime, the toolbar listens to its public lifecycle events
and correlates them with `X-HyperDjango-Debug-ID`. It records actual swap duration,
whether the target existed, exact bounded node changes, DOM bytes before and after,
focus changes, stream events, request errors, aborts, and completion.

The **Output** tab answers what the request produced. It keeps typed action/SSE items,
template operations, response content, targets and swaps, and the resulting browser DOM
changes together. It shows explicit added, removed, and changed nodes for every completed
Hyper swap, followed by the complete client event table. Changed rows include an element
identity, change type, path, and uncapped before/after descriptions in a scrollable
comparison row. It also shows selector match count, DOM byte change, focus change, swap
mode, duration, and duplicate IDs. Collection is observational: the toolbar never
modifies the page DOM to produce a diff. Snapshots are capped at 160 nodes per target and
each category retains at most 30 entries; the view marks bounded results instead of
silently implying a complete diff.

### Contract and stream diagnostics

The diagnostics section in **Overview** turns captured facts into actionable checks,
including:

- missing or ambiguous target selectors and SSE items with no correlated DOM outcome
- normalized/unknown swap modes, implicit targets, no-op and unusually large swaps
- duplicate IDs, conflicting navigation results, and browser request failures
- missing terminal SSE events, incomplete streams, duplicate event IDs, long item gaps,
  reconnect attempts, exhausted retries, and cancellations

These checks describe what was observed for the selected trace. They do not statically
prove every possible Hyper action path.

### Source navigation

Route/page classes, handlers, actions, resolved templates, and traceback frames include
their source file and line when Python or Django can resolve them. **Open source** links
use the `vscode://file` handler; browsers may ask before handing the location to VS Code.
The path and line remain visible and copyable when that handler is unavailable.

### Database context

- a deliberately compact HyperDjango SQL view that correlates request-scoped queries
  with dispatch, action, and rendering phases; use Django Debug Toolbar for its
  comprehensive general-purpose SQL inspection
- database alias, transaction state, sanitized parameters, start, and duration, with
  expandable SQL up to the configured capture bound
- normalized duplicate groups and N+1 candidates when one query shape repeats at least
  three times

The **Database** tab keeps this phase-correlated SQL context separate from the execution
waterfall. Collection is bounded at 500 queries per request.

### Output rendering and timeline

- the **Output** tab includes full-page, relative-template, block, and reusable-template
  operations, resolved template/block names, sizes, and per-render duration
- the **Timeline** tab includes a request-relative waterfall for dispatch, action,
  render, response preparation, and stream iteration; previously anonymous gaps are
  named as Django request processing,
  Django response processing, stream handoff, or finalization, while nested rows show
  their parent interval and the legend reports direct instrumentation coverage
- the Timeline SSE pacing waterfall shows time to first event and gaps between items

### Request journey

The **Timeline** tab pairs the request-relative waterfall with a short, plain-language
journey: request received, route matched, action selected, result prepared, stream
completed, browser DOM update, and request completion. Internal phase/render events are
summarized instead of repeated. Server and browser elapsed times are labeled as separate
clocks and should not be compared directly.

### Request and response

- method, full path, scheme, host, user, content type, and start time
- query parameters
- request and response headers
- response streaming state and completion status

### Errors and logs

Exceptions observed during request handling, action execution, and stream iteration are
listed with phase, qualified type, capped message, template diagnostic data, traceback
frames, source lines, and sanitized local-variable previews.

Request-scoped Python logs follow the exception details with timestamp, level, logger,
message, and source location. Log collection is bounded at 200 records per request.

## Replay safety

**Replay action** uses `Hyper.action()` with the captured path, method, action name, and
sanitized arguments. Mutating methods always require confirmation. Sensitive values are
never retained for replay; if a trace contains redactions, the confirmation warns that
`[redacted]` placeholders will be sent. Replay can repeat writes, emails, external calls,
or other side effects.

## SSE behavior

Generator actions are never consumed early for inspection. Before iteration begins,
their result is marked `not started`. The toolbar observes each item only when Django
naturally advances the stream.

During iteration, the inspector polls incremental sanitized snapshots. After
`hyper:afterRequest`, the browser reads the final trace by its
`X-HyperDjango-Debug-ID` response header. Sync and async streams are marked as one of:

- `completed`: all client-visible items were yielded
- `closed`: iteration stopped before normal completion
- `failed`: iteration raised; the exception is included in the trace

This avoids the header-time race that general-purpose AJAX toolbars encounter with
streaming responses.

## Redaction and limits

Keys containing common password, secret, token, authorization, cookie, CSRF, API-key,
access-key, or private-key fragments are displayed as `[redacted]`. Values and nested
collections are capped before they reach the in-memory store or browser. Request-header
names are not collection-capped, though sensitive values remain redacted. HTML and
JavaScript previews are capped at 1,000 characters.

`MAX_HISTORY` controls the number of request records retained per Python process. The
accepted range is 5–500 and the default is 50. History is intentionally ephemeral and
is not shared between development server processes.

The toolbar is still a powerful diagnostic surface. It can expose routes, headers,
query data, user names, application values, and exception messages. Never enable its
app, middleware, or URLs on a public production deployment.

## System checks

Run:

```bash
python manage.py check
```

The integration reports:

- `hyperdjango_devtools.W002`: toolbar enabled without its middleware
- `hyperdjango_devtools.W003`: toolbar URLs are not mounted

Checks remain silent when `HYPER_DEBUG_TOOLBAR` is disabled.

## Django Debug Toolbar compatibility

The standalone inspector is the recommended HyperDjango development experience.
HyperDjango's optional custom panel for Django Debug Toolbar remains available for
projects that prefer DJDT's SQL, cache, signal, and settings panels. See
[Django Debug Toolbar](debug-toolbar.md). Avoid enabling both HyperDjango inspectors at
the same time unless you specifically need to compare them.

## Troubleshooting

### The launcher is missing

Confirm that:

- `HYPER_DEBUG_TOOLBAR` is true
- the integration app and middleware are installed
- the response is uncompressed HTML containing `</body>`
- static files serve `hyperdjango/dev-toolbar.js`, `dev-toolbar.css`, and the
  toolbar's bundled Doto and IBM Plex Mono webfonts
- toolbar URLs are mounted and precede broad file routes

The inspector renders inside a Shadow DOM boundary. Its reset, components,
colors, and locally served fonts are independent of the application's CSS and
do not require Google Fonts or assets from the HyperDjango documentation site.

### History loads but a trace is missing

The store is process-local and bounded. A trace can disappear after an autoreload,
worker change, or enough newer requests. Increase `MAX_HISTORY` for longer sessions.

### An SSE trace remains `not started`

The response body was not iterated. If the UI finished but the record remains pending,
check the browser console for a client-side parsing error and confirm the action request
contains the `X-HyperDjango-Debug-ID` response header.

## Browser regression tests

The documentation website contains the Playwright end-to-end suite for the inspector.
It builds the website assets, starts an isolated Django development server, and drives
the toolbar through Chrome:

```bash
cd website
npm ci
npm run test:e2e
```

The suite covers the drawer and fullscreen controls, launcher movement, all inspector
views, complete headers and SQL disclosure, clipboard controls, real Hyper actions,
render and DOM diagnostics, exact and ambiguous element location, pin/pause/filter/clear
controls, action replay, exception tracebacks, completed SSE content and pacing, and
portrait and landscape layouts. Failure screenshots, videos, and traces are written to
`website/test-results/` and are ignored by Git.
