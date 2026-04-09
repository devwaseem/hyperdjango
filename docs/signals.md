# Signals

Signals are structured data patches exchanged during Hyper actions.

On requests, signals are sent to the server via `X-Hyper-Signals`.
On responses, signals are merged client-side and emitted as an event.

## What Signals Do

- pass lightweight action input without creating separate JSON endpoints
- return state patches alongside HTML swaps
- keep Alpine state in sync with server decisions

## Sending Signals to the Server

Use `$action` data (second argument):

```html
<button x-on:click="$action('search', { q, page: 1 }, { target: '#results' })">
  Search
</button>
```

The runtime serializes that data object to `X-Hyper-Signals`.

Server-side, action kwargs are merged from:

1. `X-Hyper-Signals` JSON
2. query string (`GET`)
3. form body (`POST` and others)

## Returning Signals from the Server

Return `signals` through `action_response`:

```python
return self.action_response(
    signals={"count": int(current) + 1}
)
```

You can return signals with or without HTML swaps.

Global signal keys are prefixed with `$`.

- `count` patches local Alpine component data
- `$count` patches global store data (`$hyper.count`)

Example:

```python
return self.action_response(
    signals={
        "count": 3,
        "$count": 42,
    }
)
```

## Client Merge Behavior

When response contains `signals`:

- keys prefixed with `$` are deep-merged into `Alpine.store("hyper")`
- non-prefixed keys are merged into the active Alpine component data when runtime can resolve an `x-data` root
- patch is dispatched as `hyper:signals`

This allows one response to update local component state and shared app-level store.

## Alpine Global Store Access

HyperDjango registers `$hyper` as an Alpine magic helper.

Use it in templates:

```html
<span x-text="$hyper.count"></span>
<span x-text="$hyper.stats?.active"></span>
```

`$hyper` maps to `Alpine.store("hyper")` and receives `$`-prefixed signal patches automatically.

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
@action
def increment(self, request, current=0, **params):
    return self.action_response(signals={"count": int(current) + 1})
```

### 2) Form reset after successful save

```python
return self.action_response(
    html=updated_list_html,
    target="#list",
    swap="append",
    signals={"title": "", "description": ""},
)
```

### 3) Partial swap + cross-cutting UI patch

```python
return self.action_response(
    html=row_html,
    target="#rows",
    swap="append",
    signals={"stats": {"total": total, "active": active}},
)
```

## Notes

- Signals are best for small state patches, not large document payloads.
- Keep signal keys stable; treat them like a UI contract.
- For multi-region DOM updates, combine signals with `oob`.
