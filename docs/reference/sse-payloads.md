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
| `history` | `History` | `{"push_url": "/new", "replace_url": null}` |
| `load_js` | `LoadJS` | `{"src": "/script.js"}` |

## End Event

After all action items are processed (provided no `Redirect` occurred), the runtime sends an `end` event:

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
