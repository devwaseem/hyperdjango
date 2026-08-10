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
- `X-Hyper-Request-ID`
- `Last-Event-ID` on an SSE reconnect

## SSE Reconnection

Action streams reconnect automatically after a network or response-body read failure,
or when the connection closes before an `end` or `redirect` event. The runtime uses
bounded exponential backoff: 1 second initially, doubling to a maximum
of 30 seconds, with at most 10 reconnect attempts. A valid SSE `retry:` field changes
the next retry delay.

Every action request carries a stable `X-Hyper-Request-ID`. Response events are assigned
IDs, and a reconnect sends `Last-Event-ID`; the response stream skips events the browser
already processed. The server may execute the action again during a reconnect, so actions
with non-idempotent external side effects should use `X-Hyper-Request-ID` as an idempotency
key.

The defaults can be changed globally:

```js
Hyper.configure({
  sseRetry: true,
  sseRetryInterval: 1000,
  sseRetryScaler: 2,
  sseRetryMaxWait: 30000,
  sseRetryMaxCount: 10,
});
```

To disable reconnect attempts for one action:

```js
action("save", data, { retry: false });
```

To disable them globally, call `Hyper.configure({ sseRetry: false })`.

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

### `retry`
- **Type**: `boolean`
- **Purpose**: Enables or disables automatic SSE reconnect attempts for this action.
- **Default**: `true`, unless disabled globally with `Hyper.configure({ sseRetry: false })`.

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

The HyperDjango client runtime dispatches events to `window` for lifecycle monitoring and integration. History restore events are also dispatched on `document`.

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
| `hyper:requestRetry` | Before reconnecting an interrupted SSE action stream. | `key`, `attempt`, `delay`, `error` |
| `hyper:requestRetriesFailed` | When an SSE stream exhausts its reconnect attempts. | `key`, `attempts`, `error` |
| `hyper:uploadProgress` | During file upload progress tracking. | `key`, `progress` (0-1) |
| `hyper:streamEvent` | When a new SSE event is received from the server. | `event` (type), `data` (payload) |
| `hyper:toast` | When a `Toast` action is received. | `value` |
| `hyper:history:restore:before` | Before a Back/Forward restore fetch starts. | `url`, `target`, `state` |
| `hyper:history:restore:after` | After a Back/Forward restore finishes or fails. | `url`, `target`, `state`, `success`, `error` |

## Back/Forward Restoration

The runtime listens for `popstate`. On Back or Forward it fetches
`window.location.pathname + window.location.search` with `GET` and swaps the
response into `document.body.getAttribute("hyper-pop-target") || "body"`.

It emits `hyper:history:restore:before` before the restore fetch and
`hyper:history:restore:after` after the restore finishes or fails.

For `body` restores that receive a full HTML document, the runtime extracts the
returned `<body>` contents, syncs body attributes, updates `document.title`, and
activates executable body scripts after the swap.

See [History And Back/Forward Restoration](../history.md) for the guide-level
explanation.

## Server-Side Action Detection

At dispatch time, the server treats a request as an action request when an action name is present through one of these sources:

- `X-Hyper-Action`
- query string `_action`
- POST field `_action`

Action kwargs are assembled in this order:

1. JSON from `X-Hyper-Data`
2. query parameters not already present
3. POST fields not already present for non-GET requests
