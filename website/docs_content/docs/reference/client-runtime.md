# Client Runtime Reference

## `$action(name, data, options)`

Available in Alpine environments through the HyperDjango Alpine bridge.

Arguments:

- `name: str`
  Action name to call on the server
- `data: dict[str, Any]`
  Data merged into the action kwargs
- `options: dict[str, Any]`
  Client-side request options

Request metadata sent by the runtime can include:

- `X-Hyper-Action`
- `X-Hyper-Target`
- `X-Hyper-Data`
- `X-Requested-With`

## `window.action(name, data, options)`

Plain JavaScript equivalent of `$action(...)`.

Arguments are the same as `$action(...)`.

## Action Loading Attributes

These options define how the client runtime orchestrates request lifecycle, state, and coordination.

### `form`
- **Type**: `CSS selector string | HTMLFormElement`
- **Purpose**: Associates the action with an existing form. 
- **Behavior**: 
  - Extracts method and URL from the form element.
  - Automatically serializes form fields into the action kwargs.
  - Form fields are overridden by explicit JSON action data if keys collide.

### `method`
- **Type**: `str` (e.g., `"GET"`, `"POST"`)
- **Purpose**: Explicitly overrides the request method.
- **Default**: Derived from the associated `form` if present, otherwise `"POST"` for actions.

### `url`
- **Type**: `str`
- **Purpose**: Defines the target URL for the action request.
- **Default**: The current browser URL.

### `sync`
- **Type**: `"replace" | "block" | "none"`
- **Purpose**: Defines how concurrent requests in the same coordination lane are handled.
- **Options**:
  - `replace`: Cancels the existing in-flight request and sends the new one.
  - `block`: Ignores the new request while an existing one is still in-flight.
  - `none`: Allows multiple concurrent requests to proceed.
- **Defaults**: 
  - `block` for form-backed requests.
  - `replace` for non-form requests.

### `key`
- **Type**: `str`
- **Purpose**: Identifies the specific coordination lane for `sync` behavior.
- **Behavior**: 
  - Requests with the same key share the same `sync` policy and loading state.
  - If omitted, the runtime automatically derives a key based on the action name and target.

### `onBeforeSubmit`
- **Type**: `(requestOptions) => void | boolean`
- **Purpose**: Client-side hook immediately before the request is dispatched.
- **Behavior**: If it returns `false`, the request is aborted. Useful for client-side validation.

### `onUploadProgress`
- **Type**: `(progressEvent) => void`
- **Purpose**: Enables tracking for multipart/form-data upload progress.
- **Behavior**: Provides access to `loaded` and `total` bytes for UI progress indicators.

## Outcomes

Common outcome flags:

- `blocked`
- `aborted`
- success with no special flag

Rejected cases:

- network failure
- thrown client/runtime exception

Meaning:

- `blocked`: the request never started because `sync="block"` rejected it
- `aborted`: the request started, but a later request replaced it
- success: the request completed and the response was processed normally

## Runtime Events

The HyperDjango client runtime dispatches events to `window` for lifecycle monitoring and integration.

| Event | Fired When | Payload Properties |
| :--- | :--- | :--- |
| `hyper:beforeRequest` | Immediately before sending an action request. | `key`, `url`, `method`, `action` |
| `hyper:afterRequest` | After a request completes or fails. | `key` |
| `hyper:requestBlocked` | When `sync="block"` prevents a new request. | `key` |
| `hyper:requestReplaced` | When `sync="replace"` aborts an in-flight request. | `key` |
| `hyper:requestAborted` | When a request is intentionally cancelled. | `key` |
| `hyper:requestSuccess` | When a request completes successfully. | `key`, `status` |
| `hyper:requestError` | When the server returns an error status. | `key`, `status`, `message` |
| `hyper:requestException` | When client-side code throws an exception. | `key`, `error` |
| `hyper:uploadProgress` | During file upload progress tracking. | `key`, `progress` (0-1) |
| `hyper:streamEvent` | When a new SSE event is received from the server. | `event` (type), `data` (payload) |
| `hyper:toast` | When a `Toast` action is received. | `value` |


## Server-Side Action Detection

At dispatch time, the server treats a request as an action request when an action name is present through one of these sources:

- `X-Hyper-Action`
- query string `_action`
- POST field `_action`

Action kwargs are assembled in this order:

1. JSON from `X-Hyper-Data`
2. query parameters not already present
3. POST fields not already present for non-GET requests
