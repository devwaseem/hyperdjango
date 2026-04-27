# Declarative HTML APIs

Most client-side behavior should go through `$action(...)` or `window.action(...)`.

These HTML APIs are still especially useful when you want less inline JavaScript.

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
