# Runtime Events and SSE Payload

HyperDjango communicates action outcomes to the client using Server-Sent Events (SSE) with `content-type: text/event-stream`.

## Event Format

Action-item events are serialized as:

```
event: <event_name>
data: <json_payload>

```

Ordinary action-item events do not carry IDs. A GET action can instead yield an explicit
named `Checkpoint`; its control-only wire event carries this ID:

```
event: checkpoint
id: <request_id>:checkpoint:<name>

```

After processing the checkpoint, the runtime records its ID. If that same GET stream is
retried, the runtime keeps its `X-Hyper-Request-ID` and sends the checkpoint ID in
`Last-Event-ID`. The action uses `get_resume_checkpoint(...)` to decide which completed
stages it can skip; the server does not automatically replay or discard action items.

The parser accepts LF, CRLF, and CR line endings as required by the SSE format.

## Heartbeat Comments

While a generator action is idle, HyperDjango emits a standard SSE comment at the
configured heartbeat interval:

```
: heartbeat

```

The default interval is 15 seconds and can be changed with
`HYPER_SSE_HEARTBEAT_INTERVAL`; set it to `0` to disable heartbeats. Comments are
transport-only frames: the client parser ignores them, they carry no event ID or data,
and they do not advance `Last-Event-ID`, dispatch `hyper:streamEvent`, or change the
retry policy. Heartbeats keep an otherwise idle connection active, while the existing
reconnect and checkpoint behavior handles connections that still fail.

## Action SSE Events

| Event Name | Item Type | Payload Example |
| :--- | :--- | :--- |
| `patch_signals` | `Signal` | `{"name": "count", "value": 1}` |
| `patch_signals` | `Signals` | `{"a": 1, "b": 2}` |
| `patch_html` | `HTML` | `{"content": "...", "swap": "outer", "target": "#id"}` |
| `patch_html` | `Delete` | `{"target": "#id", "content": "", "swap": "delete"}` |
| `toast` | `Toast` | `{"value": "Saved!"}` |
| `dispatch_event`| `Event` | `{"name": "my-event", "payload": {...}, "target": "#id"}` |
| `redirect` | `Redirect` | `{"url": "/new"}` |
| `checkpoint` | `Checkpoint` | No data payload; `id: <request_id>:checkpoint:<name>` |
| `switch_action` | `SwitchAction` | `{"name":"watch","data":{"job_id":"..."},"method":"GET"}` |
| `history` | `History` | `{"push_url": "/new", "replace_url": null}` |
| `load_js` | `LoadJS` | `{"src": "/script.js"}` |

## Checkpoint event

`Checkpoint(name)` marks a completed stage in a retryable GET stream. The event is
control-only: it does not dispatch an application event or produce a DOM update.

Checkpoint names must match `[A-Za-z0-9][A-Za-z0-9._-]{0,63}` and must be emitted at
most once per response. Checkpoints require a valid `X-Hyper-Request-ID` and are rejected
on non-GET streams.

```python
from hyperdjango import Checkpoint, get_resume_checkpoint
from hyperdjango.actions import HTML, action

CHECKPOINTS = ("summary", "rows", "complete")


@action(method="GET")
def watch_report(self, request, report_id):
    resume = get_resume_checkpoint(request, allowed=CHECKPOINTS)
    completed = resume.index if resume else -1

    if completed < 0:
        yield HTML(self.render_summary(report_id), target="#summary", swap="inner")
        yield Checkpoint("summary")

    if completed < 1:
        yield HTML(self.render_rows(report_id), target="#rows", swap="inner")
        yield Checkpoint("rows")

    if completed < 2:
        yield HTML(self.render_complete(report_id), target="#status", swap="inner")
        yield Checkpoint("complete")
```

`get_resume_checkpoint(request, allowed=...)` returns a `ResumeCheckpoint` with `name`
and its zero-based `index` in the ordered allow-list. It returns `None` for a first
request and for malformed, stale, cross-request, unknown, or non-GET cursors, so the
action restarts from the beginning. The allow-list must contain unique, valid names.

Treat `Last-Event-ID` as untrusted client input and a progress hint only. Always run
normal authentication, authorization, tenant, and resource checks before using it to
skip work. Keep checkpoint names and their ordering stable across deployments, or
version them and safely restart when a cursor is no longer valid.

Checkpoints do not preserve a Python generator, make GET side effects safe, or store job
state. A retry is a new request and may reach another worker. State needed for
correctness must live in shared durable storage, and work performed before a checkpoint
must be safe to repeat if the connection drops before the browser acknowledges that
marker. A new action call, page reload, or `SwitchAction` destination gets a new request
ID and does not inherit an earlier stream's checkpoint.

## Switch action event

Application code normally produces this event with a Python action reference:

```python
return self.watch_build.switch_to(job_id=str(job.pk))
```

The destination's `@action(method=...)` declaration supplies `name` and `method`.
`data` contains the signature-validated destination arguments. A cross-endpoint
`.at(...)` handoff may also add a locally reversed `url`. Raw or external destination
URLs are not accepted by the Python API. Retry is deliberately absent from the wire
payload because it is a client transport policy.

After accepting `switch_action`, the browser terminates the source stream successfully
and starts the destination through the normal action pipeline. The destination receives
a new `X-Hyper-Request-ID`, no source `Last-Event-ID`, the incremented
`X-Hyper-Switch-Depth`, and a retry default recomputed from the destination method. GET
destinations retry by default; POST destinations do not. Reconnects of a GET destination
reuse its new request ID and send only its own latest checkpoint in `Last-Event-ID`.

The payload contains routing and transport metadata, not a claim of idempotency. If the
source response is lost before this event reaches the browser, no destination request is
started.

## End Event

After all action items are processed (provided no `Redirect` or `SwitchAction` occurred),
the runtime sends an `end` event. Both `redirect` and `switch_action` are terminal, so
items after either event are not serialized:

```
event: end
data: {}
```

## Error Event

If an action fails, an `error` event is sent:

```
event: error
data: {"status": 500, "message": "Something went wrong"}
```
