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

@action(method="POST")
def start_package_build(self, request, package_id):
    job = start_package_build(package_id=package_id)
    return self.watch_package_build.switch_to(job_id=str(job.pk))

@action(method="GET")
def watch_package_build(self, request, job_id):
    for snapshot in watch_job(job_id):
        yield HTML(self.render_job(snapshot), target="#package-build-status")
```

```html
<button @click="$action('start_package_build', { package_id }, {
  method: 'POST', key: 'package-build'
})">Build</button>
```

Retry is a client transport policy. GET requests retry by default, while POST requests
do not; an explicit client `retry: true` or `retry: false` overrides either default.
The Python `@action` decorator does not accept retry metadata.

`switch_to()` validates the destination's Python signature and returns a `SwitchAction`.
Use keyword arguments for clarity; they become destination action data. Parameters
already supplied by the current route are validated but are not duplicated in action
data. Missing, unknown, duplicated, and unsupported variadic positional arguments fail
on the server before a switch payload is emitted.

`SwitchAction` is terminal, like `Redirect`; later yielded items are not delivered. It
does not navigate. The runtime transfers the request lane and loading lifecycle, emits
`hyper:actionSwitch`, and starts the destination with a new `X-Hyper-Request-ID`, no
inherited `Last-Event-ID`, and a retry default recomputed from the destination method.
Thus a POST command does not retry, while a switched GET watcher does. `url` defaults to
the current action URL; `at()` can replace it only with a locally reversed Django route. Chains are limited to four
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

The action reference still supplies the wire name and HTTP method. `at()` supplies only
URL routing. HyperDjango resolves the route with Django `reverse()`, checks
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

Actions used as switch destinations must explicitly declare their HTTP method:

```python
@action(method="GET")
```

Declared methods are enforced by server dispatch. Legacy `@action` declarations remain
valid for ordinary calls, but cannot be switch destinations until `method` is declared.
The switch wire payload does not contain retry metadata. The browser independently
applies its method-aware policy to the destination, and does not inherit the source
request's explicit retry option.

Important safety constraints:

- `switch_to()` does not make the command idempotent. POST requests do not retry by
  default; enable `retry: true` only when the command is safe to execute again.
- If the command response is lost before the switch reaches the browser, the watcher
  cannot start. The command must leave durable, queryable state so refresh can discover
  its outcome.
- The destination must be safe to execute again. A read-only watcher must not write
  database state, enqueue work, initialize a workflow, send messages, or call mutating
  external APIs.
- Use named `Checkpoint` markers only after completed stages, and emit idempotent
  replacement patches when a changing read model cannot reproduce incremental output.
- HTTP method selects the client retry default; it is not proof of safety. GET watchers
  must remain read-only, and explicitly retryable POST commands must be idempotent.

Use a durable idempotency ledger when a command explicitly enables automatic retry,
when losing the handoff response is unacceptable, or when an external side effect needs
exactly-once coordination.

## Adopting Reliable Streams in an Existing Project

After upgrading HyperDjango, deploy the updated `hyper.js` with the Python package. Run
`collectstatic` again in production and invalidate any CDN or long-lived static asset
cache that could keep serving the previous runtime. Projects that copied `hyper.js` into
their own source tree must replace that copy or switch back to the packaged static file.

The client owns the retry decision. GET requests retry by default according to
`Hyper.configure({ sseRetry: ... })`; POST requests do not. A per-call boolean
`retry` option overrides either method default. A valid SSE `retry:` field may adjust
the delay, but cannot enable reconnects.

### Resume a GET stream from named checkpoints

A retry creates a new Django request; it cannot continue the old generator frame. Yield
a named `Checkpoint` after each completed stage, then inspect the acknowledged marker at
the beginning of the next request:

```python
from hyperdjango import Checkpoint, get_resume_checkpoint
from hyperdjango.actions import HTML, action

CHECKPOINTS = ("summary", "rows", "complete")


@action(method="GET")
def stream_report(self, request, report_id):
    resume = get_resume_checkpoint(request, allowed=CHECKPOINTS)
    completed = resume.index if resume else -1

    if completed < 0:
        yield HTML(self.render_summary(report_id), target="#summary", swap="inner")
        yield Checkpoint("summary")

    if completed < 1:
        yield HTML(self.render_rows(report_id), target="#rows", swap="inner")
        yield Checkpoint("rows")

    if completed < 2:
        yield HTML(self.render_status(report_id), target="#status", swap="inner")
        yield Checkpoint("complete")
```

Each marker is sent without a data payload:

```
event: checkpoint
id: <request-id>:checkpoint:<name>

```

The runtime treats it as a control event, records it only after preceding stream work
has been processed, and sends it as `Last-Event-ID` if the same GET request reconnects.
`get_resume_checkpoint(...)` validates the method, request ID, wire format, and ordered
allow-list. It returns a `ResumeCheckpoint(name, index)` for a recognized marker, or
`None` so the action safely starts from the beginning.

Checkpoint names must be unique in the allow-list and in each response, and must match
`[A-Za-z0-9][A-Za-z0-9._-]{0,63}`. Keep names and their order stable across deployments.
Checkpointing is explicit: ordinary action events have no automatic sequence IDs, and
HyperDjango neither replays nor skips them for you.

Treat `Last-Event-ID` and `X-Hyper-Request-ID` as untrusted correlation values, never as
authentication or authorization. Run all permission and tenant checks before skipping a
stage. A marker lives in the client request lifecycle, not durable server storage; page
reloads, new action calls, switches, browser changes, and worker restarts do not restore
application state. Persist correctness-critical progress in the database or another
shared durable store. Work before a marker must also be safe to repeat if the connection
drops before the browser acknowledges it.

A hand-built `StreamingHttpResponse` is outside HyperDjango's action-item serializer. It
must emit and validate its own stable checkpoint contract, or the caller should disable
retries.

### Make explicitly retried POST actions idempotent

POST requests do not retry unless the client passes `retry: true`. If a POST must be
retryable, deduplicate its side effects with the stable request ID:

1. Read `X-Hyper-Request-ID` from the request.
2. Store it with a unique constraint in shared, durable storage.
3. Reuse the stored outcome when the same ID appears again.
4. Use the same ID as the idempotency key for downstream services that support one.

```python
from django.db import transaction


@action(method="POST")
def charge(self, request):
    request_id = request.headers["X-Hyper-Request-ID"]

    with transaction.atomic():
        attempt, created = PaymentAttempt.objects.get_or_create(
            request_id=request_id,
            defaults={"status": "pending"},
        )
        if created:
            attempt.complete_once()

    return HTML(
        content=self.render_payment(attempt),
        target="#payment-status",
        swap="inner",
    )
```

```html
<button @click="$action('charge', {}, { method: 'POST', retry: true })">Pay</button>
```

Do not rely on a process-local dictionary or cache for correctness: a reconnect may
reach another worker. Explicitly retried POST actions still need ordinary CSRF,
authentication, and authorization checks.

### Check the streaming path

Every proxy and middleware layer must pass event-stream chunks through promptly. In
particular:

- keep proxy buffering and caching disabled for action streams;
- exclude `text/event-stream` responses from middleware that buffers compression output;
- set the upstream read timeout longer than the longest expected pause between events;
- preserve `X-Hyper-Request-ID` and `Last-Event-ID` request headers;
- preserve `Content-Type: text/event-stream`, `Cache-Control`, and
  `X-Accel-Buffering: no` response headers.

HyperDjango emits `end` automatically for normal action streams and treats `redirect`
and `switch_action` as terminal. A custom event-stream response must also finish with an
`end`, `redirect`, or `switch_action` event; otherwise a retry-enabled client correctly
treats the close as an interruption.

### Rollout checklist

- Verify a normal streamed action reaches its terminal event.
- Interrupt a GET stream after a checkpoint and confirm the next request includes
  `<request-id>:checkpoint:<name>` in `Last-Event-ID`.
- Confirm the resumed action skips the acknowledged block and emits the next checkpoint.
- Confirm GET retries by default and POST does not.
- If a POST explicitly enables retries, confirm its idempotency ledger prevents repeated
  side effects.
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
