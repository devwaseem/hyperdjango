# Actions

Actions are the server-side interaction API of HyperDjango.

Use page handlers like `get()` and `post()` for full-page rendering.

Use `@action` for interaction-level updates.

## What an Action Is

An action is a method marked with `@action`.

```python
from __future__ import annotations

from hyperdjango.actions import HTML, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def save(self, request):
        return [HTML(content="<div id='flash'>Saved</div>", target="#flash")]
```

Actions let the server tell the browser to:

- patch HTML
- remove elements
- dispatch browser events
- show toasts
- redirect
- update history
- load JavaScript
- patch Alpine signals when Alpine integration is in use

## Recommended Return Shapes

The clearest action return styles are:

`list of action items`

Use a list when the whole response is known immediately.

```python
from __future__ import annotations

from hyperdjango.actions import HTML, Toast, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def create(self, request):
        return [
            HTML(content="<li>New item</li>", target="#todo-list", swap="append"),
            Toast(payload={"type": "success", "message": "Created"}),
        ]
```

`generator of action items`

Use a generator when items should be streamed over time.

```python
from __future__ import annotations

from time import sleep

from hyperdjango.actions import HTML, Redirect, Toast, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def run_job(self, request):
        yield HTML(content="<p id='job-status'>Starting...</p>", target="#job-status")
        sleep(1)
        yield HTML(content="<p id='job-status'>Working...</p>", target="#job-status")
        sleep(1)
        yield Toast(payload={"type": "success", "message": "Done"})
        yield Redirect(url="/done/")
```

Treat `Redirect(...)` as the last action item. Once the runtime sends a redirect, later items are not delivered.

## Command-to-query handoff with `switch_to()`

An action reference's `switch_to()` method builds a terminal `SwitchAction` internally,
ending a short command stream and starting a separate action through the normal client
pipeline. Use it when a bounded transaction or durable enqueue should not be retried,
but the resulting durable state needs a long-lived, retryable watcher.

```python
from hyperdjango.actions import HTML, action

@action(method="POST", retry=False)
def start_package_build(self, request, package_id):
    job = start_package_build(package_id=package_id)
    return self.watch_package_build.switch_to(job_id=str(job.pk))

@action(method="GET", retry=True)
def watch_package_build(self, request, job_id):
    for snapshot in watch_job(job_id):
        yield HTML(self.render_job(snapshot), target="#package-build-status")
```

```html
<button @click="$action('start_package_build', { package_id }, {
  method: 'POST', retry: false, key: 'package-build'
})">Build</button>
```

`switch_to()` validates the destination's Python signature and returns a `SwitchAction`.
Use keyword arguments for clarity; they become destination action data. Parameters
already supplied by the current route are validated but are not duplicated in action
data. Missing, unknown, duplicated, and unsupported variadic positional arguments fail
on the server before a switch payload is emitted.

`SwitchAction` is terminal, like `Redirect`; later yielded items are not delivered. It
does not navigate. The runtime transfers the request lane and loading lifecycle, emits
`hyper:actionSwitch`, and starts the destination with a new `X-Hyper-Request-ID`, no
inherited `Last-Event-ID`, and the destination's own retry policy. `url` defaults to the
current action URL; `at()` can replace it only with a locally reversed Django route. Chains are limited to four
switches by default; configure the browser with `switchActionMaxDepth` and Django with
`HYPER_SWITCH_ACTION_MAX_DEPTH` when a longer legitimate chain is required. Application
code should normally use `switch_to()` rather than instantiate `SwitchAction` directly.

The [live command-to-query demo](/#switch-action-demo) deliberately interrupts its
destination watcher. It displays both request IDs, the reconnect state, and the command
execution count while keeping one loading indicator active across the handoff.

### Cross-endpoint handoffs

Use `at()` with a Django route name when the destination action belongs to another page:

```python
return BuildDetailPage.watch_package_build.at(
    "packages:build-detail",
    route_kwargs={
        "tenant_slug": tenant.slug,
        "package_id": package.pk,
    },
    query={"panel": "status"},
).switch_to(job_id=str(job.pk))
```

The action reference still supplies the wire name, HTTP method, and retry policy. `at()`
supplies only URL routing. HyperDjango resolves the route with Django `reverse()`, checks
that the referenced action belongs to the resolved page, rejects absolute/external
URLs, and keeps route kwargs separate from action data. This respects namespaces,
mount prefixes, converters, and normal Django URL escaping. Raw destination URLs are
not accepted.

For a different route handled by the same page class, the bound form is also valid:

```python
return self.watch_package_build.at(
    "packages:build-detail",
    route_kwargs={"package_id": package.pk},
).switch_to(job_id=str(job.pk))
```

Actions used as switch destinations must explicitly declare both transport properties:

```python
@action(method="GET", retry=True)
```

Declared methods are enforced by server dispatch. Legacy `@action` declarations remain
valid for ordinary calls, but cannot be switch destinations until `method` and `retry`
are declared. There is no per-switch override, preventing a call site from weakening
the destination action's transport contract. The declared retry value controls
server-driven switches only; direct JavaScript or Alpine calls still use their own
`retry` option. The originating command must therefore still be invoked with
`retry: false` as shown above.

Important safety constraints:

- `switch_to()` does not make the command idempotent. Invoke a non-idempotent command
  with `retry: false`.
- If the command response is lost before the switch reaches the browser, the watcher
  cannot start. The command must leave durable, queryable state so refresh can discover
  its outcome.
- The destination must be safe to execute again. A read-only watcher must not write
  database state, enqueue work, initialize a workflow, send messages, or call mutating
  external APIs.
- Read-only is not the same as deterministic. Sequence-based `Last-Event-ID` resumption
  assumes a reconnect can reproduce the same ordered events. If a changing read model
  cannot do that, emit idempotent replacement patches (for example, replace one status
  node with the latest snapshot) or set `retry=False` and implement an explicit fresh
  snapshot/reconnect policy by declaring `@action(..., retry=False)` on the destination.
- HyperDjango never infers mutation safety from the HTTP method and never silently
  changes retry behavior.

Use a durable idempotency ledger when the command itself must survive automatic retry,
when losing the handoff response is unacceptable, or when an external side effect needs
exactly-once coordination.

## Adopting Reliable Streams in an Existing Project

After upgrading HyperDjango, deploy the updated `hyper.js` with the Python package. Run
`collectstatic` again in production and invalidate any CDN or long-lived static asset
cache that could keep serving the previous runtime. Projects that copied `hyper.js` into
their own source tree must replace that copy or switch back to the packaged static file.

No action signature or return type needs to change. The client adds a stable
`X-Hyper-Request-ID`, the server assigns ordered event IDs, and a reconnect sends
`Last-Event-ID` so events already applied in the browser are skipped.

This automatic behavior applies to responses produced through HyperDjango's action
response pipeline. A view that returns a hand-built `StreamingHttpResponse` must assign
stable event IDs and honor `Last-Event-ID` itself, or explicitly disable retries for the
client call.

### Make side effects idempotent

A reconnect is a new HTTP request and can execute the action again. Event resumption
prevents duplicate DOM patches, but it does not by itself prevent duplicate database
writes, emails, payments, jobs, or calls to another service.

For an action with non-idempotent side effects:

1. Read `X-Hyper-Request-ID` from the request.
2. Store it with a unique constraint in shared, durable storage.
3. Reuse the stored outcome when the same ID appears again.
4. Yield events in the same order when replaying the outcome, allowing
   `Last-Event-ID` to resume at the correct position.

```python
from django.db import transaction


@action
def charge(self, request):
    request_id = request.headers["X-Hyper-Request-ID"]

    with transaction.atomic():
        attempt, created = PaymentAttempt.objects.get_or_create(
            request_id=request_id,
            defaults={"status": "pending"},
        )
        if created:
            attempt.complete_once()

    yield HTML(
        content=self.render_payment(attempt),
        target="#payment-status",
        swap="inner",
    )
```

Use the same request ID as the idempotency key when calling a downstream service that
supports one. Do not rely on a process-local dictionary or cache for correctness: a
reconnect may reach another application worker. Treat the header as an opaque correlation
value, not as authentication or authorization.

If an action cannot safely be retried yet, opt out while migrating it:

```html
<button @click="$action('charge', {}, { retry: false })">Pay</button>
```

The plain JavaScript equivalent is `action("charge", {}, { retry: false })`. To opt out
for the whole application, use `Hyper.configure({ sseRetry: false })`.

### Check the streaming path

Every proxy and middleware layer must pass event-stream chunks through promptly. In
particular:

- keep proxy buffering and caching disabled for action streams;
- exclude `text/event-stream` responses from middleware that buffers compression output;
- set the upstream read timeout longer than the longest expected pause between events;
- preserve `X-Hyper-Request-ID` and `Last-Event-ID` request headers;
- preserve `Content-Type: text/event-stream`, `Cache-Control`, and
  `X-Accel-Buffering: no` response headers.

HyperDjango emits `end` automatically for normal action streams and treats `redirect` and `switch_action` as
terminal. A custom event-stream response must also finish with an `end`, `redirect`, or `switch_action`
event; otherwise the client correctly treats the close as an interruption and retries.

### Rollout checklist

- Verify a normal streamed action reaches its terminal event.
- Interrupt a stream after one event and confirm the next request includes
  `Last-Event-ID`.
- Confirm the first event is not applied twice after reconnecting.
- Confirm a `retry: false` action makes only one request when interrupted.
- Test through the same reverse proxy, CDN, and worker topology used in production.
- Monitor `hyper:requestRetry`, `hyper:requestRetriesFailed`, and
  `hyper:requestException` during rollout.

See [Runtime Events and SSE Payload](reference/sse-payloads.md) for the wire format and
[Client Runtime Reference](reference/client-runtime.md) for retry configuration and
lifecycle events.

## Other Supported Return Shapes

The current runtime also accepts a few other return forms.

`single action item`

```python
from __future__ import annotations

from hyperdjango.actions import HTML, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def save(self, request):
        return HTML(content="<div id='flash'>Saved</div>", target="#flash")
```

`Actions(...)`

```python
from __future__ import annotations

from hyperdjango.actions import Actions, HTML, Toast, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def create(self, request):
        return Actions(
            HTML(content="<li>New item</li>", target="#todo-list", swap="append"),
            Toast(payload={"type": "success", "message": "Created"}),
        )
```

`str`

```python
from __future__ import annotations

from hyperdjango.actions import action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def simple(self, request):
        return "<div id='flash'>Saved</div>"
```

`dict`

A `dict` is treated as context for block rendering from the current page template.

```python
from __future__ import annotations

from hyperdjango.actions import action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def stats(self, request):
        return {"count": 12, "completed": 4}
```

```django
{% block stats %}
  <div><strong>{{ count }}</strong> total, <strong>{{ completed }}</strong> completed</div>
{% endblock stats %}
```

`HttpResponse`

```python
from __future__ import annotations

from django.http import HttpResponse

from hyperdjango.actions import action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def download(self, request):
        return HttpResponse("ok", content_type="text/plain")
```

## Typed Action Items

### `HTML`

Use `HTML(...)` to patch HTML into the page.

```python
from __future__ import annotations

from hyperdjango.actions import HTML, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def save(self, request):
        return [
            HTML(
                content="<div id='flash'>Saved</div>",
                target="#flash",
                swap="outer",
                transition=True,
                focus="preserve",
            )
        ]
```

### `Delete`

Use `Delete(...)` to remove a target element.

```python
from __future__ import annotations

from hyperdjango.actions import Delete, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def remove_row(self, request, id: int):
        return [Delete(target=f"#row-{id}")]
```

### `Event`

Use `Event(...)` to dispatch a browser `CustomEvent`.

```python
from __future__ import annotations

from hyperdjango.actions import Event, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def save_profile(self, request):
        return [Event(name="profile:saved", payload={"message": "Saved"}, target="#panel")]
```

### `Toast`

Use `Toast(...)` to emit a toast payload.

```python
from __future__ import annotations

from hyperdjango.actions import Toast, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def save(self, request):
        return [Toast(payload={"type": "success", "message": "Saved"})]
```

### `Redirect`

Use `Redirect(...)` when the interaction should leave the current page.

```python
from __future__ import annotations

from hyperdjango.actions import Redirect, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def finish(self, request):
        return [Redirect(url="/dashboard/")]
```

### `History`

Use `History(...)` when the URL should change without leaving the current page.
`push_url` adds a browser history entry; `replace_url` updates the current entry.

```python
from __future__ import annotations

from hyperdjango.actions import History, HTML, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def filter(self, request, q: str = ""):
        return [
            History(replace_url=f"/search/?q={q}"),
            HTML(content=f"<div id='results'>Results for {q}</div>", target="#results"),
        ]
```

When the user presses Back or Forward, HyperDjango fetches the restored URL and
swaps the response into the pop target. See [History And Back/Forward
Restoration](history.md) for the full restoration model, target behavior, and
body script handling.

### `LoadJS`

Use `LoadJS(...)` when an action-loaded fragment needs its own JS module.

```python
from __future__ import annotations

from hyperdjango.actions import HTML, LoadJS, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def open_modal(self, request):
        partial = self.render_template(
            "partials/confirm_modal",
            request=request,
            context_updates={"title": "Confirm", "message": "Continue?"},
        )
        items = [HTML(content=partial.html, target="#modal-root", swap="inner")]
        if partial.js:
            items.append(LoadJS(src=partial.js))
        return items
```

### `Signal` and `Signals`

Signals are Alpine-oriented state patches.

```python
from __future__ import annotations

from hyperdjango.actions import action
from hyperdjango.integrations.alpine.actions import Signal, Signals
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def counter(self, request, count: int = 0):
        return [Signal(name="count", value=int(count) + 1)]

    @action
    def increment_both(self, request, current: int = 0):
        local_count = int(current) + 1
        global_count = 42
        return [Signals(values={"count": local_count, "$count": global_count})]
```

- `count` patches the nearest Alpine `x-data`
- `$count` patches `Alpine.store("hyper")`
