# Changelog

All notable changes to this project will be documented in this file.

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
