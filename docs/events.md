# Events

HyperDjango emits browser events on `window` for request lifecycle, transitions, signals, and forms.

Events let apps integrate analytics, observability, and UI libraries (toasts, progress bars, logging) without forking runtime behavior.

## Request Lifecycle

### `hyper:beforeRequest`

Triggered right before `fetch()` starts for a Hyper request.

Typical use:

- request logging
- per-request instrumentation

### `hyper:requestSuccess`

Triggered after a response is received with a `2xx` HTTP status.

Typical use:

- success metrics
- response timing markers

### `hyper:requestError`

Triggered after a response is received with a non-`2xx` HTTP status.

Typical use:

- error metrics
- centralized error toasts/logging

For action requests, non-`2xx` responses are still parsed and applied when they contain actionable SSE/JSON/HTML content (for example validation fragments, redirects, signals, or toasts). `hyper:requestError` still fires so callers can observe the status code.

When an action stream emits an explicit server error event, `hyper:requestError` also carries a structured `message` field.

### `hyper:requestException`

Triggered when request execution throws (network/runtime error), excluding intentional aborts.

Typical use:

- network failure monitoring
- fallback UI handling

### `hyper:afterRequest`

Triggered when request handling finishes (success, error, or abort), after in-flight bookkeeping is updated.

Typical use:

- cleanup hooks
- final timing/trace events

Common detail fields for lifecycle events:

- `id`: request id
- `key`: resolved sync/request key
- `url`, `method`
- `kind`: `action|visit|nav-form` (when available)
- `action`, `target` (for action requests)
- `status`, `ok`, `response` (when response exists)

### `hyper:uploadProgress`

Triggered during request-body uploads when `onUploadProgress` is provided on a request.

Common detail fields:

- `id`: request id
- `url`, `method`
- `kind`: `action|visit|nav-form` (when available)
- `action`, `target` (for action requests)
- `loaded`, `total`
- `lengthComputable`
- `progress`: `0..1` when total size is known, otherwise `null`

## Sync and Cancellation

### `hyper:requestBlocked`

Triggered when sync mode is `block` and a matching in-flight request already exists, so the new request is skipped.

### `hyper:requestReplaced`

Triggered when sync mode is `replace` and a matching in-flight request is aborted in favor of the new one.

### `hyper:requestAborted`

Triggered when a request is aborted via `AbortController` (for example by replacement logic).

Sync detail fields include:

- `key`: resolved sync key
- `mode`: `replace|block|none`
- `replacedId`: present on `hyper:requestReplaced`

## Swap and Transition

### `hyper:swap:start`

Triggered just before target DOM mutation begins (before swap delay + mutation).

### `hyper:swap:end`

Triggered immediately after the swap mutation has finished.

### `hyper:settle:end`

Triggered after settle delay/class handling completes.

### `hyper:transition:start`

Triggered when a View Transition starts (`transition: true` and browser support present).

### `hyper:transition:end`

Triggered when the active View Transition finishes (or settles after failure).

## Data and Notifications

### `hyper:signals`

Triggered by the Alpine integration when it receives a `patch_signals` stream event and applies the patch to Alpine state/store.

### `hyper:toast`

Triggered once per toast item when a response includes `toast`/`toasts`.

## Form Events

### `hyper:form:beforeSubmit`

Triggered immediately before a form-driven action submit is dispatched.

### `hyper:form:success`

Triggered when a form-driven action request completes without being blocked/aborted and without throwing.

### `hyper:form:blocked`

Triggered when form request is blocked by sync mode.

### `hyper:form:aborted`

Triggered when form request is aborted (for example by replacement).

### `hyper:form:error`

Triggered when a form cannot submit (for example missing action) or when request processing throws.

Form detail commonly includes:

- `action`, `method`, `url`
- `target`, `key`
- `result` (for success)
- `error` (for error)

## Convenience Request State Events

### `hyper:request:start`

Triggered when global pending request count transitions from `0` to `>0`.

### `hyper:request:end`

Triggered when global pending request count transitions from `>0` to `0`.

These are useful for global loading bars/overlays when per-target indicators are not enough.

## Example Listener

```javascript
window.addEventListener("hyper:toast", (event) => {
  const toast = event.detail || {};
  console.log("toast", toast.type, toast.message);
});

window.addEventListener("hyper:requestError", (event) => {
  const { status, url } = event.detail || {};
  console.warn("request error", status, url);
});
```
