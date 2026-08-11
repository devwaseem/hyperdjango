# Runtime Events and SSE Payload

HyperDjango communicates action outcomes to the client using Server-Sent Events (SSE) with `content-type: text/event-stream`.

## Event Format

Each event is serialized as:

```
event: <event_name>
id: <request_id>:<sequence_number>
data: <json_payload>

```

The `id` line is included for requests made by the Hyper client runtime. On reconnect,
the runtime sends the last processed ID in `Last-Event-ID`, and the server resumes after
that event. The parser accepts LF, CRLF, and CR line endings as required by the SSE format.

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
| `switch_action` | `SwitchAction` | `{"name":"watch","data":{"job_id":"..."},"method":"GET","retry":true}` |
| `history` | `History` | `{"push_url": "/new", "replace_url": null}` |
| `load_js` | `LoadJS` | `{"src": "/script.js"}` |

## Switch action event

Application code normally produces this event with a Python action reference:

```python
return self.watch_build.switch_to(job_id=str(job.pk))
```

The destination's `@action(method=..., retry=...)` declaration supplies `name`,
`method`, and `retry`; callers cannot override them at the switch site. `data` contains
the signature-validated destination arguments. A cross-endpoint `.at(...)` handoff may
also add a locally reversed `url`. Raw or external destination URLs are not accepted by
the Python API.

After accepting `switch_action`, the browser terminates the source stream successfully
and starts the destination through the normal action pipeline. The destination receives
a new `X-Hyper-Request-ID`, no source `Last-Event-ID`, the incremented
`X-Hyper-Switch-Depth`, and its declared retry policy. Reconnects of that destination
then reuse its new request ID and send only its own latest `Last-Event-ID`.

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
