# Changelog

All notable changes to this project will be documented in this file.

## 0.20.0

- Removed `OOB` from the action/runtime model and simplified multi-region updates to use multiple targeted `HTML(...)` and `Delete(...)` items.
- Removed `oob` from `action_response(...)` and deleted old runtime support for `patch_oob` events.
- Shifted action UI control fully to the server for normal action calls: targets, swaps, transitions, focus, history, and related patch behavior now come from server-returned items.
- Narrowed `$action(...)` to request concerns such as `data`, `form`, `method`, `url`, `sync`, `key`, and `onUploadProgress`.
- Updated examples and docs to reflect the server-owned patch model and the removal of OOB updates.

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
