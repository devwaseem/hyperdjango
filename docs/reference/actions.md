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

Optional transport metadata:

```python
@action(method="GET")
def watch(self, request, job_id):
    ...
```

- `method: Literal["GET", "POST"]` declares and enforces the accepted HTTP method
- actions may omit `method`, but such actions cannot be `switch_to()` destinations
- retry is not action metadata; the client defaults GET requests to retry and POST
  requests not to retry, with an explicit client `retry` option taking precedence

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

## `Checkpoint(name)`

Import:

```python
from hyperdjango import Checkpoint
```

Arguments:

- `name: str`

Behavior:

- marks a completed stage in a resumable GET action stream
- emits a control-only `checkpoint` event with ID
  `<X-Hyper-Request-ID>:checkpoint:<name>`
- does not produce a DOM update or application event
- requires a GET request and a valid `X-Hyper-Request-ID`
- each name may be emitted only once in a response
- names must match `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`

Yield a checkpoint after the action items for a completed stage. On a reconnect, use
`get_resume_checkpoint(...)` to select the next stage; HyperDjango does not
automatically skip action items.

## `get_resume_checkpoint(request, *, allowed)`

Import:

```python
from hyperdjango import get_resume_checkpoint
```

Arguments:

- `request: HttpRequest`
- `allowed: Sequence[str]`, the unique ordered checkpoint names recognized by the
  current action

Return value:

- `ResumeCheckpoint(name, index)` when `Last-Event-ID` is a valid checkpoint for this
  GET request and its `X-Hyper-Request-ID`
- `None` for an initial request or a malformed, stale, cross-request, unknown, or
  non-GET cursor

`index` is the checkpoint's zero-based position in `allowed`. The header is untrusted
client input: use it only after normal authentication and authorization, and keep all
correctness-critical job state in shared durable storage. A retry is a new request, not
a continuation of the original Python generator.

## `action.switch_to(*args, **kwargs)`

Preferred API for constructing a terminal `SwitchAction`:

```python
return self.watch_build.switch_to(job_id=str(job.pk))
```

Behavior:

- binds arguments against the referenced action's Python signature after `self` and
  `request`
- validates required, unknown, duplicated route, and positional arguments
- derives the wire name and HTTP method from `@action`
- inherits the current endpoint and client workflow lane
- builds `SwitchAction` internally; direct construction is not normally needed

## `action.at(route, *, route_kwargs=None, query=None).switch_to(...)`

Cross-endpoint form:

```python
return BuildPage.watch_build.at(
    "packages:build-detail",
    route_kwargs={"package_id": package.pk},
    query={"panel": "status"},
).switch_to(job_id=str(job.pk))
```

- `route` is a Django URL-pattern name, including namespaces when applicable
- `route_kwargs` are passed to `django.urls.reverse()` and used for signature validation
- `query` is encoded with `doseq=True`
- the resolved view must be the page that owns the referenced action
- only application-local reversed paths are accepted; raw and external URLs are not
  supported

## `SwitchAction`

`SwitchAction` is the typed terminal value produced by `switch_to()`. It remains part of
`ActionItem` for normalization, inspection, typing, and custom integrations.

Behavior:

- terminal for the current stream; later items are not delivered
- starts a normal action request without navigation
- gives the destination a new request ID and no inherited checkpoint
- omits retry from the wire payload; the client recomputes the destination default from
  its method (GET retries, POST does not)
- transfers lane/loading ownership across the logical workflow
- emits `switch_action` on SSE and `hyper:actionSwitch` in the browser
- does not make the originating command idempotent

## `History(push_url=None, replace_url=None)`

Arguments:

- `push_url: str | None = None`
- `replace_url: str | None = None`

Behavior:

- `push_url` adds a history entry
- `replace_url` replaces the current history entry
- no full redirect occurs
- Back/Forward restoration re-fetches the restored URL and swaps the response into `hyper-pop-target`, defaulting to `body`
- full-document responses restored into `body` are normalized to their returned `<body>` contents, with `document.title` and body attributes synced
- executable body scripts from a full-document restore are activated after the swap; external scripts whose `src` already existed before the swap are skipped

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
