# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

- Updated the public website for the 0.38.0 release with a version-synchronized homepage badge, a release highlights section, clearer command documentation, current upgrade guidance, complete website routes for every linked guide/reference/example page, and browser coverage that prevents future version drift.
- Fixed the Library CI matrix to install the optional Django Debug Toolbar dependency required by its integration tests, and made the website Dockerfile pass Trivy's destination-path validation.
- Fixed the standalone request inspector scrolling long pages to the bottom while rendering its tab strip or restoring an open drawer after refresh.

## 0.38.0

- Added `hyper_runserver`, a single Django development command that supervises Django and Vite, preserves Django autoreloading, automatically assigns a free Vite port, accepts normal `runserver` host/port arguments, and supports automatic Django port selection.
- Added unified development output with a compact URL/readiness banner, `[django]` and `[vite]` log prefixes, preserved ANSI colors, package-manager detection, Vite readiness checks, coordinated process shutdown, and actionable startup failures.
- Added `hyper_runserver` options for fixed or public Vite hosts and ports, Bun/pnpm/Yarn/npm selection, browser opening, verbose Vite output, and Django-only operation.
- Added Django system checks for route compilation, frontend configuration, colocated Vite entries, and missing or stale production manifests.
- Updated new scaffolds and the bundled example projects to Vite 8, and documented its Node.js `>=20.19` requirement.
- Updated the website Docker and publishing workflow to build from the repository context and install the local HyperDjango package without relying on an editable parent-directory dependency in the deployed image.
- Corrected the client runtime reference to reflect that `_action` is accepted from POST form data but intentionally ignored in GET query strings.
- Added a standalone HyperDjango Request Inspector with independent assets, bounded request history, route/action/output inspection, execution and SSE waterfalls, sanitized request/response data, exception tracebacks, and final sync/async stream metadata.
- Expanded the inspector with actual browser swap outcomes, exact DOM locating, explicit added/removed/changed diffs, per-item SSE content and pacing, SQL/N+1 diagnostics, request-scoped logs, payload costs, action replay, contextual copy controls, and per-trace pinning alongside pause, clear, search, and filters.
- Added contract and stream-health diagnostics, Python/template source navigation, SSE retry, stall, cancellation, terminal-event and target-outcome analysis, responsive bottom-drawer/fullscreen layouts, and a simplified eight-tab information architecture.
- Added a dedicated file-route inspector with URL-to-directory resolution, page/template/layout sources, HTTP handlers, route action inventory, Vite entry files, resolved assets, and current-document load status; the Overview now shows the human route identity instead of its generated class name.
- Made `HYPER_DEBUG_TOOLBAR` the authoritative inspector enablement switch independently of Django's `DEBUG` setting, while retaining `DEBUG`-guarded setup as the recommended development convention.
- Enabled the Request Inspector on the HyperDjango website as a live demonstration and added eight Playwright scenarios covering the complete toolbar, real actions, exceptions, completed SSE streams, DOM outcomes, controls, independent assets, and responsive layouts with `DEBUG=False`.
- Added the standalone and Django Debug Toolbar guides to the website documentation registry and generated `/llms.txt` corpus.
- Updated the Django Debug Toolbar panel after SSE iteration completes so sync and async generator actions report their yielded item types and sanitized metadata without being consumed early.
- Made interrupted SSE action streams reconnect with bounded exponential backoff, `retry:` support, event IDs, and `Last-Event-ID` resume semantics.
- Added per-action `retry: false` and global `sseRetry: false` options for disabling automatic SSE reconnect attempts.
- Added native browser connectivity state, network lifecycle events, declarative online/offline class toggles, and offline-aware SSE reconnection.
- Fixed SSE parsing for CRLF and CR line endings in addition to LF.

### Project upgrade notes

- Existing projects are not rewritten automatically by `hyper_scaffold`. Update the project's `package.json` to use `"vite": "^8.0.0"`, use Node.js `>=20.19` (or `>=22.12`), and regenerate the package-manager lockfile before committing the upgrade. For npm projects, run `npm install` and verify `npm run build`.
- Replace separate Django and Vite development terminals with `python manage.py hyper_runserver`. Keep a project-local `package.json` with a `dev` script that starts Vite. Existing `runserver` addresses remain valid, including `0.0.0.0:8000`; use `--vite-public-host` when browsers must reach Vite through a different LAN, container, or remote-development hostname.
- Existing fixed `HYPER_VITE_DEV_SERVER_URL` settings may remain for developers who still use Django's ordinary `runserver`. While `hyper_runserver` is active, it temporarily supplies its selected Vite URL to the Django process and restores the previous environment afterward. Use `--vite-port` and `--vite-public-host` when a managed development server needs stable or externally reachable Vite coordinates.
- Do not use `?_action=...` links to invoke actions. Call actions through HyperDjango's client runtime, which sends `X-Hyper-Action`, or submit `_action` in POST form data. Ordinary GET query strings now always remain page-navigation state.
- Resolve new `hyperdjango.*` system-check errors instead of silencing them by default. Development projects should have a valid Vite configuration and colocated entries; production images should run `npm run build` before Django checks so `HYPER_VITE_OUTPUT_DIR/.vite/manifest.json` exists and is newer than its source entries.
- Monorepos that install HyperDjango through a local path dependency must use the repository root as the Docker build context and copy the HyperDjango package metadata and source before `uv sync`. Projects installing a published HyperDjango release from PyPI do not need this Docker change.
- `HYPER_DEBUG_TOOLBAR=True` now enables the standalone inspector regardless of `DEBUG`. Existing `if DEBUG:` configuration remains valid and recommended; deployments that set the toolbar flag outside that condition should review access to traces and debugging controls.
- No Alpine or morphing migration is required. HyperDjango remains usable without Alpine, continues to prefer Alpine Morph when Alpine is available, and retains morphdom as the framework-independent fallback.

#### Adopting the HyperDjango Request Inspector

The inspector is optional and has no external runtime dependency. Existing projects
that do not enable it require no changes. To add it, register the app and place its
middleware near the start of the middleware list so it surrounds HyperDjango dispatch:

```python
INSTALLED_APPS += ["hyperdjango.integrations.devtools"]

MIDDLEWARE = [
    "hyperdjango.integrations.devtools.middleware.HyperDjangoDebugToolbarMiddleware",
    *MIDDLEWARE,
]

HYPER_DEBUG_TOOLBAR = True
HYPER_DEBUG_TOOLBAR_CONFIG = {
    "MAX_HISTORY": 50,
    "URL_PREFIX": "__hyperdebug__",
}
```

If the project uses `GZipMiddleware`, place the inspector middleware immediately after
it so toolbar injection occurs before compression. Mount the inspector endpoints before
HyperDjango's broad file routes, and keep the mounted prefix synchronized with
`HYPER_DEBUG_TOOLBAR_CONFIG["URL_PREFIX"]`:

```python
from django.urls import include, path
from hyperdjango.urls import include_routes

urlpatterns = [
    path(
        "__hyperdebug__/",
        include("hyperdjango.integrations.devtools.urls"),
    ),
    *include_routes(),
]
```

`HYPER_DEBUG_TOOLBAR` is the authoritative switch and is intentionally independent of
Django's `DEBUG` setting. Most projects should wrap the app, middleware, setting, and
URLs in their existing `if DEBUG:` development configuration. Projects enabling it
with `DEBUG=False` must serve HyperDjango's packaged static assets through their normal
production static-file pipeline and should explicitly control who can access sanitized
request metadata, SQL, exception details, replay, pause, pin, and clear controls.

The toolbar keeps a bounded, process-local history. Configure `MAX_HISTORY` for the
expected development workload, and remember that histories are not shared between
workers and disappear on process restart. Do not enable both the standalone inspector
and HyperDjango's optional Django Debug Toolbar panel unless both interfaces are
intentionally required.

## 0.37.0
- Breaking: HyperDjango no longer dispatches actions from the `_action` query parameter on GET requests. Actions should be invoked through the `X-Hyper-Action` header used by HyperDjango's client runtime, or through POST form data.
- Added an optional first-class Django Debug Toolbar panel with request-local route, action, render, result, exception, and timing diagnostics; sensitive action values are redacted and streaming generators are not consumed for inspection.
- Added Django Debug Toolbar configuration checks and full-body navigation refresh support, with documented `UPDATE_ON_FETCH`, middleware, panel, and URL setup.
- Kept `hyper-loading` active until response bodies are parsed and caller response handling finishes, including awaited swap lifecycles through settle completion for actions, visits, SSE events, and plain navigation forms.

## 0.36.0
- Emit history events in both window and document
## 0.35.0
- Added CSP nonce support for HyperDjango's shipped runtime scripts.
- Added the `{% hyper_csp_nonce %}` template tag for reading Django's request CSP nonce.
- Propagated the active page nonce to dynamically inserted module scripts and scripts activated from partial HTML.

## 0.34.0
- Activated newly inserted inline and external body scripts during full-document history restores while avoiding duplicate execution for scripts already present before the swap.
- Added `hyper:history:restore:before` and `hyper:history:restore:after` events around Back/Forward restoration.
- Made Back/Forward restoration default to `body` when `hyper-pop-target` is omitted from the page.
- Added a dedicated History guide documenting URL restoration, pop targets, full-document swaps, body script activation, and restore lifecycle events.

## 0.33.0
- Fixed browser back/forward restoration after `History(...)` updates by safely handling full-document responses during body swaps.
- Added a `/history-demo/` example that exercises `History(push_url=...)` and browser Back restoration.

## 0.31.0
- Fixed SSE streaming for async action generators so yielded events flush incrementally with pauses preserved on both sync and async request paths.

## 0.30.0
- Removed the `replace` flag from `Redirect` so redirect actions always perform a normal browser navigation and use a single SSE payload shape.

## 0.29.0
- Fixed HyperView dispatch so Django class-based view setup runs correctly for sync and async handlers, restoring `self.request` for mixins and keeping async `get(...)` / `post(...)` support working.

## 0.27.0
- Fixed async `HyperView` routing so `async def get(...)` and `async def post(...)` work without Django trying to await a plain `HttpResponse`.
- Fixed async `@action` support for both awaited return values and async generators that stream SSE updates.
- Fixed SSE behavior under ASGI/Uvicorn by streaming through async iterators when available.
- Updated the example app and website routes to exercise async handlers and async streaming directly.

## 0.26.0
- Added async page handler support so `async def get(...)`, `async def post(...)`, and other async HTTP method handlers work through the normal `dispatch` path.
- Added async action support so `async def` `@action` methods are awaited correctly.
- Fixed SSE streaming under ASGI by using async streaming responses where appropriate, preventing production buffering behavior with Uvicorn.
- Added async iterable support for streamed action responses.
- Updated examples and the website to exercise async handlers and async streaming actions directly.

## 0.25.0
- Restructured documentation into a comprehensive reference guide with exhaustive parameter and functionality details.
- Added explicit reference pages for Actions, Client Runtime, HTML Loading APIs, Asset Resolver, SSE Payloads, and Exceptions.
- Refined runtime events and shortcuts (`render_template_page`, `render_template_block`) documentation.
- Completed removal of route-local `layout.py` support by cleaning up unused internal routing helper functions.

## 0.24.0
- Renamed the request data header from `X-Hyper-Signals` to `X-Hyper-Data` and removed the old fallback.
- Clarified and updated the docs around request/action data flow, signals, and the current core vs Alpine integration split.

## 0.23.0

- Added `default_app_config`.

## 0.22.0

- Added `hyper-loading-class` and `hyper-loading-remove-class` for htmx-style class toggling during active requests.
- Reused the existing loading identifiers (`hyper-loading`, `hyper-loading-key`, `hyper-loading-action`) as the scope controls for loading class toggles.
- Removed the root `<html hyper-loading>` marker so request activity no longer mutates the document element with that attribute.
- Renamed the preferred transition naming attribute to `hyper-view-transition-name` while keeping `hyper-view-name` as a backward-compatible alias.
- Updated docs and examples to reflect the new loading class behavior and the preferred view-transition attribute name.

## 0.21.0

- Added automatic target inference for `HTML(...)` patches from the root element id in returned HTML when no explicit target is provided.
- Explicit server `target` still takes priority over inferred ids.
- Changed the default `HTML(...)` swap mode to `outer` so returned fragments replace their root target by default.

## 0.20.0

- Removed `OOB` from the action/runtime model and simplified multi-region updates to use multiple targeted `HTML(...)` and `Delete(...)` items.
- Removed `oob` from `action_response(...)` and deleted old runtime support for `patch_oob` events.
- Shifted action UI control fully to the server for normal action calls: targets, swaps, transitions, focus, history, and related patch behavior now come from server-returned items.
- Narrowed `$action(...)` to request concerns such as `data`, `form`, `method`, `url`, `sync`, `key`, and `onUploadProgress`.
- Added `Event(name=..., payload={...}, target=None)` as a first-class typed action item for dispatching browser events, defaulting to `window` when no target selector is provided.
- Split Alpine support out of core into `hyper-alpine.js`; core `hyper.js` is now Alpine-agnostic while the Alpine bridge auto-detects Alpine and installs `$action` plus signal patching.
- Moved `Signal` and `Signals` to `hyperdjango.integrations.alpine.actions` while keeping compatibility imports from `hyperdjango.actions`.
- Changed core signal handling so framework-agnostic integrations should use `hyper:streamEvent`, while `hyper:signals` is emitted by the Alpine bridge only.
- Removed public `ErrorMessage` from the action API and kept exception-to-error-event conversion as internal runtime behavior.
- Prefer Alpine Morph for HTML patch morphing when Alpine is present, with `morphdom` retained as the non-Alpine fallback.
- Fixed frontend autoreload registration by connecting the watcher at module import time instead of `AppConfig.ready()`.
- Updated scaffold output, examples, and docs to reflect the Alpine integration split, the `title` context pattern, and the renamed multi-patch workflow guide.

## 0.19.0

- Logged Hyper action exceptions through Django's request logger before converting them into SSE error responses.
- Preserved structured action error handling for the client while making `runserver` output visible again for `PermissionDenied`, `Http404`, and unexpected action exceptions.

## 0.18.0

- Added `Delete(target=...)` as a first-class typed action item for removal flows.
- Compiled `Delete(...)` into the existing `patch_html` transport with `swap: "delete"` behind the scenes.
- Updated the todo example to use `Delete(...)` instead of `swap="delete"`.
- Updated docs to recommend `Delete(...)` and the explicit single-patch `OOB(...)` form in the typed action item model.

## 0.17.0

- Added `Actions(...)` as a common typed wrapper for returning multiple action items without spelling out large union list annotations.
- Changed action failure handling to prefer exceptions for `403`, `404`, and `500` instead of `action_response(status=...)`.
- Converted action exceptions like `PermissionDenied` and `Http404` into structured SSE error events.
- Merged structured action error payloads into `hyper:requestError`, including a `message` field when available.
- Added a new `/error-demo` example showing how to catch `hyper:requestError` and turn server-generated failures into UI toasts and inline error states.

## 0.16.0

- Refined typed OOB patches so `OOB` now represents a single explicit patch item (`content`, `target`, `swap`) instead of a wrapped payload batch.
- Kept `action_response(oob=...)` compatibility by compiling legacy selector-keyed OOB payloads into multiple single-patch `OOB(...)` items.
- Fixed the profile example action signature so form POST fields passed through action kwargs no longer conflict with the handler.

## 0.15.1

- Refined typed OOB patches so `OOB` now represents a single explicit patch item (`content`, `target`, `swap`) instead of a wrapped payload batch.
- Kept `action_response(oob=...)` compatibility by compiling legacy selector-keyed OOB payloads into multiple single-patch `OOB(...)` items.
- Fixed the profile example action signature so form POST fields passed through action kwargs no longer conflict with the handler.

## 0.15.0

- Switched action responses to SSE-framed event streams, including one-shot actions.
- Added typed action items such as `Signal`, `Signals`, `HTML`, `Toast`, `OOB`, `Redirect`, `History`, and `LoadJS`.
- Added generator-based action streaming support for incremental live updates from the server.
- Updated the runtime to parse and apply streamed action events like `patch_signals`, `patch_html`, `toast`, `patch_oob`, `redirect`, `history`, `load_js`, and `end`.
- Added a new `/sse-demo` example showing a long-running streamed action with live progress and appended server log updates.
- Updated examples, scaffold output, and primary docs to prefer typed action items over monolithic `action_response(...)` payloads.

## 0.14.1

- Fixed action upload progress wiring so `$action(..., { onUploadProgress })` correctly switches to the XHR upload path.
- Fixed the upload progress example so both `window.action(...)` and Alpine `$action(...)` show live progress updates.

## 0.14.0

- Added upload progress support for `$action(...)` via the `onUploadProgress` option.
- Added the `hyper:uploadProgress` browser event for building upload progress UIs.
- Documented how to correlate upload progress using request `key` and `id`.

## 0.13.1

- Fixed non-form `POST` actions to send a URL-encoded request body with `_action`.
- Kept form-backed actions using real `FormData` uploads.
- Improved action dispatch reliability for imperative `POST` calls.
