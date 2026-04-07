# Action Response Reference

`Page.action_response(...)` returns an `ActionResult` payload consumed by the Hyper runtime.

## Core Fields

- `html`: response fragment for target swap
- `target`: CSS selector for target swap
- `swap`: swap mode
- `status`: HTTP status code
- `headers`: custom response headers

## UX Fields

- `toast` / `toasts`: emits `hyper:toast`
- `focus`: post-swap focus policy
- `transition`: enables View Transition when supported
- `swap_delay`: delay before swap (ms)
- `settle_delay`: settle delay (ms)

## Data and Multi-Region Fields

- `signals`: state patch payload
- `oob`: out-of-band DOM operations

## History Fields

- `push_url`: push browser history entry
- `replace_url`: replace current history entry

## Safety Fields

- `strict_targets`: fail when target is missing

## Example

```python
return self.action_response(
    html=self.render_block(
        request=request,
        block_name="save_profile",
        context_updates={"form": form},
    ),
    target="#profile-panel",
    swap="outer",
    focus="first-invalid",
    transition=True,
    swap_delay=40,
    settle_delay=120,
    toast={"type": "success", "message": "Saved"},
    signals={"profile": {"dirty": False}},
    oob={"#flash": {"swap": "inner", "html": "<p>Saved</p>"}},
)
```
