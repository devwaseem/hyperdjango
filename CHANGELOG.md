# Changelog

All notable changes to this project will be documented in this file.

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
