# Changelog

All notable changes to this project will be documented in this file.

## 0.14.0

- Added upload progress support for `$action(...)` via the `onUploadProgress` option.
- Added the `hyper:uploadProgress` browser event for building upload progress UIs.
- Documented how to correlate upload progress using request `key` and `id`.

## 0.13.1

- Fixed non-form `POST` actions to send a URL-encoded request body with `_action`.
- Kept form-backed actions using real `FormData` uploads.
- Improved action dispatch reliability for imperative `POST` calls.
