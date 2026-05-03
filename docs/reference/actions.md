# Actions Reference

## `@action`

Import:

```python
from hyperdjango.actions import action
```

Usage forms:

```python
@action
def save(self, request):
    ...
```

```python
@action("save_profile")
def save(self, request):
    ...
```

Behavior:

- marks the method as an action
- stores the action name used by the runtime
- the action becomes discoverable through `get_action(name)`

## `Actions(*items)`

Import:

```python
from hyperdjango.actions import Actions
```

Purpose:

- wrapper around multiple typed action items

Arguments:

- `*items: ActionItem`

Notes:

- iterable at runtime
- functionally equivalent to returning a list of action items

## Return Shapes

Recommended:

- list of action items
- generator yielding action items

Supported by the current runtime:

- single action item
- `Actions(...)`
- `str`
- `dict`
- `HttpResponse`

Recommended guidance:

- use a list when the whole response is known immediately
- use a generator when the response should stream over time
- use typed action items for clarity

Dispatch compatibility details:

- `str` is converted into a patch action
- `dict` is treated as context for `render_block(...)`
- `HttpResponse` is passed through after Hyper headers are ensured

## `HTML(...)`

Arguments:

- `content: str | None = None`
- `target: str | None = None`
- `swap: str = "outer"`
- `transition: bool = False`
- `focus: str | None = None`
- `swap_delay: int | None = None`
- `settle_delay: int | None = None`
- `strict_targets: bool | None = None`

Argument details:

- `content`
  HTML string to patch into the page
- `target`
  CSS selector the client runtime should patch
- `swap`
  DOM insertion mode. Supported values: `inner`, `outer`, `before`, `after`, `prepend`, `append`, `delete`, `none`.
- `transition`
  Whether to request view-transition-aware patching
- `focus`
  Focus mode after patching. Common values are handled by the client runtime such as preserving focus or moving to the first invalid field.
- `swap_delay`
  Delay before the swap step starts
- `settle_delay`
  Delay before the settle step completes
- `strict_targets`
  Whether missing targets should fail loudly for this patch

Event emitted to the client runtime:

- `patch_html`

## `Delete(target)`

Arguments:

- `target: str`

Behavior:

- translated into an HTML patch with `swap="delete"`

Event emitted to the client runtime:

- `patch_html`

## `Event(name, payload=None, target=None)`

Arguments:

- `name: str`
- `payload: dict[str, Any] | None = None`
- `target: str | None = None`

Behavior:

- if `target` is provided, the event is dispatched on that element
- otherwise the event is dispatched on `window`

Event emitted to the client runtime:

- `dispatch_event`

## `Toast(payload)`

Arguments:

- `payload: Any`

Behavior:

- emitted to the client as `hyper:toast`
- your frontend chooses how to display it

Event emitted to the client runtime:

- `toast`

## `Redirect(url)`

Arguments:

- `url: str`

Behavior:

- redirects the browser immediately
- if returned from a list or generator, treat it as the last item because later items are not delivered

Event emitted to the client runtime:

- `redirect`

## `History(push_url=None, replace_url=None)`

Arguments:

- `push_url: str | None = None`
- `replace_url: str | None = None`

Behavior:

- `push_url` adds a history entry
- `replace_url` replaces the current history entry
- no full redirect occurs

Event emitted to the client runtime:

- `history`

## `LoadJS(src)`

Arguments:

- `src: str`

Behavior:

- loads a module script dynamically after the action response reaches the client

Event emitted to the client runtime:

- `load_js`

## `Signal(name, value)`

Arguments:

- `name: str`
- `value: Any`

Behavior:

- `count` patches the nearest Alpine `x-data`
- `$count` patches `Alpine.store("hyper")`

Event emitted to the client runtime:

- `patch_signals`

## `Signals(values)`

Arguments:

- `values: dict[str, Any]`

Behavior:

- patches multiple Alpine values at once

Event emitted to the client runtime:

- `patch_signals`
