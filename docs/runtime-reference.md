# Runtime Reference

HyperDjango runtime is served from `hyperdjango/static/hyperdjango/hyper.js` and auto-initializes on page load.

If Alpine is present, `hyperdjango/static/hyperdjango/hyper-alpine.js` auto-detects it and installs the Alpine bridge.

The runtime translates server responses into predictable browser behavior (swap, history, loading, events) while keeping HTML as the primary transport.

Action responses are now consumed as SSE-framed event streams, even for normal one-shot actions. The server closes the stream immediately after the last event.

## Global API

- `window.Hyper`
- `window.action(action, data, options)`
- `window.Hyper.configure({ strictTargets: boolean })`

When Alpine is present, HyperDjango installs the `$action(...)` Alpine magic automatically.

For Alpine-specific signal behavior, see `docs/signals.md`.

## `action` signature

```javascript
$action(name, data, options)
```

- `data`: plain object payload for the action
- `options`: transport and UX options

## `action` options

`$action(...)` now focuses on request concerns. Swap target, swap mode, transition, focus, history, and related UI behavior are expected to come from server-returned action items such as `HTML(...)`, `Delete(...)`, `Redirect(...)`, and `History(...)`.

- `form`: `HTMLFormElement` or CSS selector; when present Hyper infers `method` and `url` from the form
- `method`: defaults to `GET`, unless a form is provided and its `method` says otherwise
- `data`: object payload for non-form calls, or extra fields merged into a form submit
- `url`: defaults to current path
- `sync`: `replace|block|none`
- `key`: sync group key
- `onUploadProgress`: callback for upload progress detail during body uploads

## Action Stream Events

The action runtime applies explicit SSE event names from the server, including:

- `patch_signals`
- `patch_html`
- `dispatch_event`
- `toast`
- `history`
- `redirect`
- `load_js`
- `end`

Example:

```javascript
 await $action("save", { email }, {
   method: "POST",
   sync: "block",
   key: "profile-save",
 });
```

Form example:

```javascript
 await $action("save_profile", {}, {
   form: "#profile-form",
   sync: "block",
 });
```

Upload progress example:

```javascript
await $action("upload_avatar", {}, {
  form: "#avatar-form",
  method: "POST",
  key: "avatar-upload",
  onUploadProgress(detail) {
    console.log(detail.key, detail.loaded, detail.total, detail.progress);
  },
});
```

For correlation, use `detail.key` when you provide an explicit `key`, or fall back to `detail.id` for a per-request identifier.

## Swap Modes

- `inner`: morph inner content (default)
- `outer`: morph element itself
- `before`: insert before target
- `after`: insert after target
- `prepend`: insert at beginning
- `append`: insert at end
- `delete`: remove target
- `none`: skip target swap

## Strict Target Handling

Strict targeting catches stale selectors and template drift early, especially during refactors.

Enable strict mode globally:

```html
<body hyper-strict-targets="true">
```

Or per call/action response with `strictTargets` / `strict_targets`.

## Multiple Patches

Server responses can emit multiple `HTML(...)` and `Delete(...)` items in one action stream.

Example typed item list:

```python
return Actions(
    HTML(content=main_html, target="#todo-list", swap="append"),
    HTML(content=stats_html, target="#todo-stats"),
    HTML(content=flash_html, target="#flash"),
)
```

## Generic Stream Event Hook

Framework-agnostic integrations can listen to the core event stream directly:

```javascript
window.addEventListener("hyper:streamEvent", (event) => {
  console.log(event.detail.event, event.detail.data);
});
```

Alpine signal patching is implemented on top of this stream in `hyper-alpine.js`.

## Loading Indicators

Loading attributes provide consistent feedback/disable behavior without custom spinner wiring in each component.

Attributes:

- `hyper-loading`: show while requests are active
- `hyper-loading-delay="150"`: delay indicator visibility
- `hyper-loading-action="search"`: action scoped
- `hyper-loading="search-key"` or `hyper-loading-key="search-key"`: key scoped
- `hyper-loading-disable`: disable controls during requests
- `hyper-loading-disable="search-key"` or `hyper-loading-disable-key="search-key"`: key scoped disable
- `hyper-target-busy="#selector"`: mirrors busy state for target selector

The runtime also toggles:

- `<html hyper-loading>`
- `aria-busy` on `<html>`, `<body>`, and known targets

## Navigation Enhancement

`hyper-nav` enhances links and forms (opt-in only).

Opt-in navigation keeps native browser behavior by default and progressively enhances only where partial navigation is beneficial.

`hyper-no-nav` explicitly disables enhancement for a specific element. If both attributes are present, `hyper-no-nav` wins and the browser performs a normal navigation/submit.

Link attributes:

- `hyper-nav`
- `hyper-target` (default `body`)
- `hyper-sync`, `hyper-key`
- `hyper-transition`, `hyper-swap-delay`, `hyper-settle-delay`, `hyper-focus`

For enhanced navigation forms, use normal `hyper-nav` form attributes.

Back/forward behavior fetches into `body[hyper-pop-target]` (default `body`).

To explicitly disable enhancement for a specific node:

```html
<a href="/export.csv" hyper-nav hyper-no-nav>Export</a>
```

## Transitions and Lifecycle Classes

Lifecycle classes/events make animation and instrumentation deterministic around DOM mutations.

During swap lifecycle on target:

- adds `hyper-swapping`
- then adds `hyper-settling`

Set view names declaratively:

```html
<section hyper-view-name="profile-panel"></section>
```

Runtime maps it to CSS `view-transition-name`.
