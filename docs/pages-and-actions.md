# Pages and Actions

Pages and actions separate full-page rendering from interaction-level updates. Keep standard Django request handlers for initial load, then add focused `@action` methods for partial updates, signals, and UX metadata.

## `HyperView` Class

Create page classes in each route file:

```python
from hyperdjango.page import HyperView


class PageView(HyperView):
    def get(self, request):
        return {"title": "Home"}
```

For non-routed template packages, use `HyperPageTemplate` instead (see `docs/guides/template-packages.md`).

If you only need action semantics in a custom class, use `HyperActionMixin`.

Handler return types:

- `dict` -> rendered with route template (`index.html` by default)
- `str` -> raw `HttpResponse`
- `HttpResponse` -> passed through

## Templates

- default template is `index.html` next to `page.py`
- `render(request=...)` renders full template
- `render_block(block_name=...)` renders only one block from the template

## `@action`

Actions are methods decorated with `@action`:

Actions provide a stable server contract for incremental updates without introducing a second API layer.

```python
from hyperdjango.actions import action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def details(self, request, slug=""):
        return {"slug": slug}
```

You can rename action entrypoint:

```python
@action("save_profile")
def save(self, request):
    ...
```

## Action Inputs

Action kwargs are merged from:

1) `X-Hyper-Signals` JSON header
2) query string (`GET`)
3) form body (`POST`/others)

`_action` is reserved and ignored as data input.

Input merging lets actions be called consistently from links, forms, and JS helpers without special endpoint variants.

## Action Return Types

- typed item list/generator -> streamed to the browser as SSE-framed action events
- `ActionResult` -> compatibility path compiled into the same SSE event stream
- `dict` -> render matching template block (`X-Hyper-Target` or action name)
- `str` -> HTML patch response
- `HttpResponse` -> passthrough with cache/vary hardening

## Typed Action Items

Preferred action style is to return typed items such as:

- `HTML(content, target=..., swap=...)`
- `Delete(target=...)`
- `Toast(payload=...)`
- `Redirect(url=..., replace=False)`
- `History(push_url=..., replace_url=...)`
- `LoadJS(src=...)`
- `Event(name=..., payload={...}, target=None)`

When Alpine integration is in use, you can also return:

- `Signal(name, value)`
- `Signals({...})`

Example:

```python
from hyperdjango.actions import Event, HTML, Toast, action
from hyperdjango.integrations.alpine.actions import Signal


@action
def save(self, request):
    return [
        Signal(name="profile", value={"dirty": False}),
        Toast(payload={"type": "success", "message": "Saved"}),
        HTML(
            content=self.render_block(
                request=request,
                block_name="save_profile",
                context_updates={"form": form},
            ),
            target="#profile-form",
            swap="outer",
            focus="first-invalid",
        ),
    ]
```

These items are streamed to the client as explicit SSE events like `patch_html`, `dispatch_event`, `toast`, and `redirect`.

`HTML(...)` now defaults to `swap="outer"`.

If `target` is omitted, HyperDjango will try to infer it from the root element id in `content`.

## `action_response(...)`

`action_response(...)` still works as a compatibility helper. It now compiles into the same SSE-framed action event stream used by typed item returns.
