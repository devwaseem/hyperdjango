# History And Back/Forward Restoration

HyperDjango history is URL-driven. A history entry stores the URL, not a cached DOM snapshot. When the user presses Back or Forward, the client runtime fetches the restored URL again and swaps the response into the page.

Use this model when an interaction changes visible state and that state should be represented by the browser URL.

## Updating The URL From An Action

Return `History(...)` from an action together with any HTML patches needed for the immediate UI update.

```python
from __future__ import annotations

from hyperdjango.actions import History, HTML, action
from hyperdjango.page import HyperView


class SearchView(HyperView):
    @action
    def search(self, request, q: str = ""):
        return [
            HTML(content=f"<div id='results'>Results for {q}</div>", target="#results"),
            History(replace_url=f"/search/?q={q}"),
        ]
```

Use `replace_url` for refinements that should not create many Back-button stops, such as live search or slider changes.

Use `push_url` for meaningful states the user should be able to step back through, such as changing tabs, selecting a record, or moving between wizard steps.

```python
return [
    HTML(content=step_html, target="#wizard-step"),
    History(push_url=f"/checkout/?step={step}"),
]
```

## What Happens On Back And Forward

When the browser fires `popstate`, HyperDjango does this:

```text
Browser restores previous URL
HyperDjango emits hyper:history:restore:before
HyperDjango GETs that URL
HyperDjango swaps the response into the pop target
HyperDjango emits hyper:history:restore:after
HyperDjango does not push another history entry
```

This means every URL you push or replace should be restorable with a normal `GET`. If `/search/?q=django` is pushed into history, then `GET /search/?q=django` should render the search page with the same query state.

## Restore Lifecycle Events

The runtime emits events around Back/Forward restoration so application code can pause UI, clean up page-local integrations, or reinitialize behavior after the restored page settles.

```js
window.addEventListener("hyper:history:restore:before", (event) => {
  console.log("restoring", event.detail.url, event.detail.target);
});

window.addEventListener("hyper:history:restore:after", (event) => {
  if (event.detail.success) {
    console.log("restored", event.detail.url);
  }
});
```

Both events include:

- `url`: the restored path and query string
- `target`: the pop target selector, defaulting to `body`
- `state`: the browser `PopStateEvent.state`

The `hyper:history:restore:after` event also includes:

- `success`: whether the restore completed
- `error`: the thrown error when `success` is `false`

## The Pop Target

The Back/Forward swap target comes from `hyper-pop-target` on `<body>`.

```html
<body hyper-pop-target="#app">
```

If `hyper-pop-target` is omitted, the runtime defaults to `body`.

```html
<body>
```

The default `body` target is usually correct for full-page server-rendered routes because the restored URL can return a complete HTML document.

Use a narrower target only when every restored URL returns markup appropriate for that target.

## Full Document Responses

For Back/Forward restores into `body`, the server may return a complete document:

```html
<!doctype html>
<html>
  <head>
    <title>Search</title>
  </head>
  <body>
    ...page content...
  </body>
</html>
```

HyperDjango does not insert that entire document string inside the current body. It parses the response, extracts the returned `<body>` contents, syncs the current `<body>` attributes, and updates `document.title`.

This keeps browser history restoration compatible with normal Django page responses.

## Body Scripts On Restore

Browsers do not execute scripts inserted through `innerHTML`. HyperDjango accounts for this during full-document body restores.

After the body swap:

- inline executable body scripts run again
- external body scripts run when their `src` was not already present before the swap
- external body scripts with an already-present `src` are skipped to avoid re-running shared runtime scripts
- non-executable script types such as JSON script tags are left alone

Executable script types are:

- no `type` attribute
- `type="module"`
- `type="text/javascript"`
- `type="application/javascript"`
- `type="text/ecmascript"`
- `type="application/ecmascript"`

Prefer colocated assets and `LoadJS(...)` for action-specific JavaScript modules. Body script activation is mainly for restoring full pages that already include body scripts.

## Practical Rules

- Push URLs that can render themselves on a plain `GET`.
- Use `replace_url` for noisy state changes and `push_url` for meaningful navigation states.
- Let `hyper-pop-target` default to `body` unless you deliberately restore a smaller app shell.
- Keep action responses and full-page route responses distinct so Back/Forward restoration fetches a full page, not an action-only fragment.
- Use canonical URLs, including trailing slashes when Django `APPEND_SLASH` is enabled, to avoid extra redirects during history restoration.
- Test Back and Forward after at least two pushed states.

## Example

The example app includes `/history-demo/`. It demonstrates:

- `History(push_url=...)`
- restoring state from query parameters on normal `GET`
- Back/Forward restoration without an explicit `hyper-pop-target`
- body script activation after full-document restores
