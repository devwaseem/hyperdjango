# Signals (Alpine Integration)

Signals are an Alpine integration feature layered on top of HyperDjango core.

On requests, signal-like input data is still sent to the server via `X-Hyper-Data`.
On responses, `patch_signals` stream events are interpreted by `hyper-alpine.js`, which patches Alpine state/store and emits `hyper:signals`.

## What Signals Do

- pass lightweight action input without creating separate JSON endpoints
- return state patches alongside HTML swaps
- keep Alpine state in sync with server decisions

## Sending Signals to the Server

Use `$action` data (second argument):

```html
<button x-on:click="$action('search', { q, page: 1 })">
  Search
</button>
```

The runtime serializes that data object to `X-Hyper-Data`.

Server-side, action kwargs are merged from:

1. `X-Hyper-Data` JSON
2. query string (`GET`)
3. form body (`POST` and others)

## Returning Signals from the Server

Return `Signal(...)` or `Signals(...)` from the Alpine integration module:

```python
from hyperdjango.integrations.alpine.actions import Signal


return [Signal(name="count", value=int(current) + 1)]
```

You can return signals with or without HTML swaps.

Global signal keys are prefixed with `$`.

- `count` patches local Alpine component data
- `$count` patches global Alpine store data

Example:

```python
from hyperdjango.integrations.alpine.actions import Signals


return [Signals(values={"count": 3, "$count": 42})]
```

## Client Merge Behavior

When an action stream contains `patch_signals` and Alpine integration is active:

- keys prefixed with `$` are deep-merged into `Alpine.store("hyper")`
- non-prefixed keys are merged into the active Alpine component data when runtime can resolve an `x-data` root
- patch is dispatched as `hyper:signals`

This allows one response to update local component state and shared app-level store.

## Alpine Global Store Access

Use Alpine's normal global store access:

```html
<span x-text="$store.hyper.count"></span>
<span x-text="$store.hyper.stats?.active"></span>
```

`Alpine.store("hyper")` receives `$`-prefixed signal patches automatically when the Alpine bridge is loaded.

## Related Runtime Events

### `hyper:signals`

Fires once per response containing `signals`.

- `event.detail` is the raw signals patch payload

Example:

```javascript
window.addEventListener("hyper:signals", (event) => {
  const patch = event.detail || {};
  console.log("signals patch", patch);
});
```

Signals are also commonly used with request lifecycle events from `docs/events.md`:

- `hyper:beforeRequest`
- `hyper:requestSuccess`
- `hyper:requestError`
- `hyper:afterRequest`

## Patterns

### 1) Counter/state patch

```python
from hyperdjango.integrations.alpine.actions import Signal


@action
def increment(self, request, current=0, **params):
    return [Signal(name="count", value=int(current) + 1)]
```

### 2) Form reset after successful save

```python
from hyperdjango.actions import HTML
from hyperdjango.integrations.alpine.actions import Signals


return [
    Signals(values={"title": "", "description": ""}),
    HTML(content=updated_list_html, target="#list", swap="append"),
]
```

### 3) Partial swap + cross-cutting UI patch

```python
from hyperdjango.actions import HTML
from hyperdjango.integrations.alpine.actions import Signal


return [
    Signal(name="stats", value={"total": total, "active": active}),
    HTML(content=row_html, target="#rows", swap="append"),
]
```

## Notes

- Signals are best for small state patches, not large document payloads.
- Keep signal keys stable; treat them like a UI contract.
- For multi-region DOM updates, combine signals with multiple targeted `HTML(...)` items.
- If you are not using Alpine, prefer `Event(...)` or plain HTML patches instead of signals.
