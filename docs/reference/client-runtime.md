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
- `Last-Event-ID` with the latest acknowledged checkpoint on a GET SSE reconnect
- `X-Hyper-Switch-Depth` on a `SwitchAction` destination

## SSE Reconnection

GET action streams reconnect by default after a network or response-body read failure,
or when the connection closes before an `end`, `redirect`, or `switch_action` event.
POST action streams do not reconnect unless the caller explicitly passes `retry: true`.
An explicit boolean `retry` option always wins over the method-based default. Retry is a
client transport policy; `@action` and `SwitchAction` do not declare it.

While the browser is offline, a retry-enabled stream pauses without consuming attempts
and reconnects immediately after `hyper:network:online`. Other failures use bounded
exponential backoff: 1 second initially, doubling to a maximum of 30 seconds, with at
most 10 reconnect attempts. A valid SSE `retry:` field changes the delay for an already
enabled retry policy; it cannot enable retries.

Every action request carries a stable `X-Hyper-Request-ID`. Ordinary response events do
not receive automatic sequence IDs. A GET action can yield named `Checkpoint` markers;
the runtime records the latest marker and sends it in `Last-Event-ID` on reconnect. The
new server request calls `get_resume_checkpoint(...)` and explicitly skips completed
stages. No Python generator state is preserved, and HyperDjango does not automatically
replay or discard action items.

The defaults can be changed globally:

```js
Hyper.configure({
  sseRetry: true,
  sseRetryInterval: 1000,
  sseRetryScaler: 2,
  sseRetryMaxWait: 30000,
  sseRetryMaxCount: 10,
  switchActionMaxDepth: 4,
});
```

`sseRetry` controls the implicit GET default. It does not override an explicit per-call
`retry` value. To override either method default for one action:

```js
action("search", data, { method: "GET", retry: false });
action("idempotent_import", data, { method: "POST", retry: true });
```

To disable implicit GET retries application-wide, call
`Hyper.configure({ sseRetry: false })`.

For a server-driven handoff, the destination method comes from its Python declaration.
Retry is absent from the `switch_action` payload and is recomputed on the client from
that method, independently of the source request:

```python
@action(method="GET")
def watch_build(self, request, job_id):
    ...

return self.watch_build.switch_to(job_id=job.pk)
```

The switched GET retries according to the client's GET default; a switched POST does
not. The source call's explicit `retry` option is not inherited by either destination.

For another page endpoint, use the action reference's `at()` builder with a Django route
name. The browser still receives an ordinary `switch_action` event and runs the resolved
destination through this same client pipeline.

The source and destination are separate HTTP requests but one coordinated client
workflow. Lane ownership and matching loading/disabled state transfer before the source
releases them, preventing flicker and preventing a shared `key` from blocking or
replacing its own destination. An unrelated request using replacement synchronization,
or an explicit abort, still cancels the entire active chain. `hyper:actionSwitch`
provides the two action names and request IDs for instrumentation without exposing the
destination action data.

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
- **Default**: Derived from the associated `form` if present, otherwise `"GET"`.

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
- **Default**: GET uses `Hyper.configure({ sseRetry: ... })`, which is `true` initially;
  POST defaults to `false`.
- **Override**: Explicit `true` or `false` takes precedence over the method default and
  global GET default.

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
| `hyper:actionSwitch` | After a valid switch is received and before its destination request starts. | `originalAction`, `destinationAction`, `originalRequestId`, `newRequestId`, `key`, `method`, `url`, `retry`, `depth` |
| `hyper:toast` | When a `Toast` action is received. | `value` |
| `hyper:network:change` | When browser network availability changes. | `online`, `offline` |
| `hyper:network:online` | When the browser regains network availability. | `online`, `offline` |
| `hyper:network:offline` | When the browser loses network availability. | `online`, `offline` |
| `hyper:history:restore:before` | Before a Back/Forward restore fetch starts. | `url`, `target`, `state` |
| `hyper:history:restore:after` | After a Back/Forward restore finishes or fails. | `url`, `target`, `state`, `success`, `error` |

Control-only `checkpoint` frames update the reconnect cursor internally and are not
emitted as `hyper:streamEvent` application events.

## Network Availability

The core runtime tracks the browser's `online` and `offline` events without requiring
Alpine. Read the current state from `Hyper.network`:

```js
if (Hyper.network.online) {
  startOptionalNetworkWork();
}

window.addEventListener("hyper:network:online", () => {
  action("sync_pending_changes");
});

window.addEventListener("hyper:network:offline", () => {
  pauseOptionalNetworkWork();
});
```

Use `Hyper.network.refresh()` to resync the state from `navigator.onLine`. The runtime
also provides declarative visibility attributes that are reapplied after HTML swaps:

```html
<p hyper-offline role="status">You are offline.</p>
<p hyper-online>Connected</p>
```

Network classes follow the same add/remove model as loading classes:

```html
<main class="is-online"
      hyper-offline-class="is-offline"
      hyper-offline-remove-class="is-online">
  ...
</main>
```

`hyper-online-class` adds its classes while online, and `hyper-online-remove-class`
removes its classes while online. The corresponding `hyper-offline-class` and
`hyper-offline-remove-class` attributes apply the same behavior while offline.

Interrupted SSE action streams wait while offline and reconnect immediately when the
browser reports that the network is back. This pause does not consume the configured
SSE retry count.

Browser network availability does not guarantee that the application server is
reachable. Confirm critical recovery work with a lightweight request to the server.

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
- POST field `_action`

The `_action` query parameter is intentionally ignored on `GET` requests. Programmatic
actions, including actions using `method: "GET"`, identify the action with the
`X-Hyper-Action` header. This keeps ordinary page URLs and query strings independently
addressable and prevents a normal navigation from dispatching a page action.

Action kwargs are assembled in this order:

1. JSON from `X-Hyper-Data`
2. query parameters not already present
3. POST fields not already present for non-GET requests
