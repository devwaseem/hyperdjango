# Pages and Actions

Pages and actions separate full-page rendering from interaction-level updates. Keep standard Django request handlers for initial load, then add focused `@action` methods for partial updates, signals, and UX metadata.

## `HyperView` Class

Create page classes in each route file:

```python
from hyperdjango.page import HyperView


class HomePage(HyperView):
    def get(self, request):
        return {"title": "Home"}
```

For non-routed template packages, use `PageTemplate` instead (see `docs/guides/template-packages.md`).

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


class ProductPage(HyperView):
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

- `ActionResult` -> JSON or HTML response with Hyper metadata
- `dict` -> render matching template block (`X-Hyper-Target` or action name)
- `str` -> HTML response
- `HttpResponse` -> passthrough with cache/vary hardening

## `action_response(...)`

`Page.action_response` supports:

`action_response` centralizes interaction concerns (swap strategy, history, focus, toasts, OOB) in one explicit payload.

- `html`: swapped fragment
- `signals`: non-`$` keys patch local Alpine component data, `$`-prefixed keys patch `Alpine.store("hyper")` (`$hyper`) (explicit `bind` remains optional)
- `toast` / `toasts`: emitted as `hyper:toast` events
- `target`: CSS selector for swap target
- `swap`: `inner|outer|before|after|prepend|append|delete|none`
- `swap_delay`, `settle_delay`: milliseconds
- `transition`: enable View Transitions API for this update
- `focus`: `preserve|first-invalid|<selector>`
- `push_url`, `replace_url`: history changes
- `strict_targets`: raise if target missing
- `oob`: out-of-band operations
- `status`, `headers`

Example:

```python
return self.action_response(
    target="#profile-form",
    swap="outer",
    html=self.render_block(request=request, block_name="save_profile", context_updates={"form": form}),
    toast={"type": "success", "message": "Saved"},
    signals={"profile": {"dirty": False}},
    focus="first-invalid",
)
```
