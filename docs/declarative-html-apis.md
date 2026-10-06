# Declarative HTML APIs

Most client-side behavior should go through `$action(...)` or `window.action(...)`.

These HTML APIs are still especially useful when you want less inline JavaScript.

## Network Availability

Use `hyper-online` and `hyper-offline` to show content based on the browser's current
network availability. These attributes do not require Alpine.

```html
<p hyper-offline role="status">You are offline. Changes will sync when reconnected.</p>
<p hyper-online>Connected</p>
```

Add or remove classes in the same way as the loading APIs:

```html
<main hyper-offline-class="is-offline">
  ...
</main>

<button class="unavailable" hyper-online-remove-class="unavailable">
  Save
</button>
```

Available class attributes are:

- `hyper-online-class`
- `hyper-online-remove-class`
- `hyper-offline-class`
- `hyper-offline-remove-class`

HyperDjango reapplies the state after HTML swaps. For JavaScript lifecycle hooks and
the `Hyper.network` API, see the client runtime reference.

## `hyper-form-disable`

Use `hyper-form-disable` on a form to disable submit buttons and button-like controls while the request is active.

```html
<form id="profile-form" method="post" action="/profile" hyper-form-disable>
  {% csrf_token %}
  <input name="name" />
  <button type="button" @click="$action('save_profile', {}, { form: '#profile-form', sync: 'block' })">
    Save
  </button>
</form>
```

This is mainly submit-button protection, not a full all-input disable.

## `hyper-view-transition-name`

Use `hyper-view-transition-name` to label a DOM region for browser view transitions.

```html
<section id="profile-panel" hyper-view-transition-name="profile-panel"></section>
```

Pair it with a server response that enables transitions:

```python
from __future__ import annotations

from hyperdjango.actions import HTML, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def update_profile(self, request):
        return [
            HTML(
                content="<section id='profile-panel'>Updated</section>",
                target="#profile-panel",
                transition=True,
            )
        ]
```

## Action-Driven Lazy Loading

Lazy fragments use the current page's action endpoint rather than a separate
fragment URL:

```html
<section id="activity"
         hyper-action="load_activity"
         hyper-trigger="visible"
         hyper-action-data='{"project_id": 42}'>
  Loading activity…
</section>
```

The runtime invokes `load_activity` as a GET action once the section approaches
the viewport. The target defaults to the element's `id`; use `hyper-target` to
patch another element. `hyper-swap`, `hyper-strategy`, `hyper-transition`,
`hyper-sync`, `hyper-key`, `hyper-strict-targets`, `hyper-focus`,
`hyper-retry`, and `hyper-pause-when-hidden` use the normal action pipeline.

```python
@action(method="GET")
def load_activity(self, request, project_id: int):
    return HTML(
        content=render_activity(project_id),
        target="#activity",
        swap="inner",
    )
```

The element exposes `hyper-lazy-state="loading|loaded|error"` and emits
`hyper:lazy:start`, `hyper:lazy:success`, and `hyper:lazy:error`.

## Persistent Elements

Add `hyper-preserve` and a stable `id` to stateful DOM that must survive a
matching `inner` or `outer` response patch:

```html
<video id="preview" hyper-preserve controls></video>
```

The returned HTML must contain an element with the same `id`. HyperDjango moves
the existing node into the new DOM, preserving its JavaScript identity, media
state, focus state, and event listeners. If the response omits that `id`, the
old node is removed normally.

## Enhanced Navigation Selection

`hyper-select` selects exactly one element from a full-page response while the
request still uses the normal navigation URL:

```html
<a href="/account/"
   hyper-nav
   hyper-target="#main"
   hyper-select="#main"
   hyper-swap="inner"
   hyper-strategy="morph">
  Account
</a>
```

A missing or ambiguous selector rejects the navigation instead of patching the
wrong region. The target, selector, swap, and strategy are stored in history
state and reused for Back/Forward restoration.

## Loading APIs

Loading attributes work best when you understand `key` and request coordination from the client-side actions page.

## `hyper-loading`

Show an element while requests are active.

```html
<p hyper-loading>Loading...</p>
```

## `hyper-loading-delay`

Delay loading UI to avoid flicker.

```html
<p hyper-loading hyper-loading-delay="150">Loading...</p>
```

## `hyper-loading-action`

Scope a loading indicator to one action name.

```html
<p hyper-loading-action="search">Searching...</p>
```

## `hyper-loading-key`

Scope a loading indicator to one request key.

```html
<p hyper-loading-key="search">Searching...</p>
```

## `hyper-loading="key"`

You can also pass the key directly through `hyper-loading`.

```html
<p hyper-loading="search">Searching...</p>
```

## `hyper-loading-class`

Add classes while the matching request is active.

```html
<section hyper-loading hyper-loading-class="opacity-50">Content</section>
```

## `hyper-loading-remove-class`

Remove classes while the matching request is active.

```html
<section hyper-loading hyper-loading-remove-class="hidden" class="hidden">Loading...</section>
```

## `hyper-loading-disable`

Disable a control while requests are active.

```html
<button hyper-loading-disable>Save</button>
```

## `hyper-loading-disable-key`

Disable a control only for one request key.

```html
<button hyper-loading-disable-key="search">Search</button>
```

## `hyper-loading-disable="key"`

You can also pass the key directly through `hyper-loading-disable`.

```html
<button hyper-loading-disable="search">Search</button>
```

## `hyper-target-busy`

Mirror busy state for a specific target selector.

```html
<div hyper-target-busy="#results"></div>
```

## Loading Example

```html
<input id="search-input" />
<button @click="$action('search', { q: document.querySelector('#search-input').value }, { key: 'search' })">
  Search
</button>

<p hyper-loading-key="search" hyper-loading-delay="150">Searching...</p>
<button hyper-loading-disable-key="search">Stop double submit</button>
```
