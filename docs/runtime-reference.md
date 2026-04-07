# Runtime Reference

HyperDjango runtime is served from `hyperdjango/static/hyperdjango/hyper.js` and auto-initializes on page load.

The runtime translates server responses into predictable browser behavior (swap, OOB, history, loading, events) while keeping HTML as the primary transport.

## Global API

- `window.Hyper`
- `window.get(action, kwargs, options)`
- `window.post(action, kwargs, options)`
- `window.Hyper.configure({ strictTargets: boolean })`

Alpine magics:

- `$get(...)`
- `$post(...)`
- `$hyper` (maps to `Alpine.store("hyper")`)

For signal-specific behavior, see `docs/signals.md`.

## `get` / `post` options

These options let callers express UX behavior per interaction instead of enabling broad global behavior that is harder to reason about.

- `url`: defaults to current path
- `target`: CSS selector to swap
- `swap`: `inner|outer|before|after|prepend|append|delete|none`
- `transition`: View Transition opt-in
- `swapDelay`, `settleDelay`: delay timing (ms)
- `focus`: `preserve|first-invalid|<selector>`
- `push`, `replace`: history behavior
- `sync`: `replace|block|none`
- `key`: sync group key
- `bind`: optional explicit Alpine object to merge returned `signals` (auto-detected from active `x-data` by default)
- `syncStore`: allow `$`-prefixed signals to patch `Alpine.store("hyper")` (default `true`)
- `strictTargets`: local strict target enforcement

Example:

```javascript
await $post("save", { email }, {
  target: "#form",
  swap: "outer",
  sync: "block",
  key: "profile-save",
  transition: true,
  swapDelay: 40,
  settleDelay: 120,
  focus: "first-invalid",
});
```

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

## Out-of-Band Updates (`oob`)

`oob` lets one response update elements outside the primary `target` swap.

Use it when an action changes multiple UI regions at once (for example list + stats + flash message) and you want all updates applied from a single request.

Accepted formats:

- array of operations
- selector-keyed object

Example response payload:

```json
{
  "target": "#todo-list",
  "swap": "append",
  "html": "<li>New item</li>",
  "oob": {
    "#todo-stats": { "swap": "inner", "html": "<div>3 items</div>" },
    "#flash": { "swap": "inner", "html": "<p>Saved</p>" }
  }
}
```

Operation shape:

```json
{ "target": "#flash", "swap": "inner", "html": "...", "order": 10 }
```

`order` is used when object-style OOB entries need deterministic sequencing.

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

Form attributes are the same for navigation forms (non-`hyper-form`).

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
