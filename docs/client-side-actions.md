# Client-Side Actions

Client-side action invocation belongs in one place because this is where request coordination concepts like `sync` and `key` actually matter.

## Triggering Actions

HyperDjango exposes:

- Alpine `$action(...)`
- plain JavaScript `window.action(...)`

Alpine example:

```html
<div x-data="{ q: '' }">
  <input x-model="q" />
  <button @click="$action('search', { q }, { key: 'search' })">Search</button>
</div>
```

Vanilla JavaScript example:

```html
<input id="search-input" />
<button id="search-button" type="button">Search</button>

<script>
  document.querySelector("#search-button").addEventListener("click", () => {
    const q = document.querySelector("#search-input").value;
    window.action("search", { q }, { key: "search" });
  });
</script>
```

## `$action(name, data, options)`

```js
$action(name, data, options)
```

### `data`

The `data` object is sent to the server and merged into action kwargs.

```html
<button @click="$action('search', { q, page: 2 })">Search</button>
```

```python
from __future__ import annotations

from hyperdjango.actions import action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def search(self, request, q: str = "", page: int = 1):
        ...
```

### `form`

Use `form` when the action should submit an existing form.

```html
<form id="profile-form" method="post" action="/profile">
  {% csrf_token %}
  <input name="name" />
  <button type="button" @click="$action('save_profile', {}, { form: '#profile-form' })">
    Save
  </button>
</form>
```

When `form` is provided, HyperDjango reads the form method and action URL automatically.

### `method`

Use `method` to override the HTTP method.

```html
<button @click="$action('search', { q }, { method: 'GET' })">Search</button>
```

### `url`

Use `url` to send the action to a URL other than the current page.

```html
<button @click="$action('search', { q }, { url: '/search/' })">Search</button>
```

### `sync`

Use `sync` to control how repeated requests coordinate.

- `replace`: replace the in-flight request in the same lane
- `block`: ignore new requests while one is active
- `none`: allow concurrent requests

```html
<button @click="$action('search', { q }, { sync: 'replace' })">Live search</button>
```

```html
<button @click="$action('save_profile', {}, { form: '#profile-form', sync: 'block' })">
  Save
</button>
```

```html
<button @click="$action('append_log', {}, { sync: 'none' })">Send many</button>
```

Default behavior:

- form-backed calls default to `block`
- non-form calls default to `replace`

### `key`

Use `key` to place requests into a named coordination lane.

This affects:

- `sync` behavior
- loading indicators scoped by key
- disable states scoped by key
- upload progress correlation
- request bookkeeping in general

If two requests share a key, then `sync: 'replace'` or `sync: 'block'` applies across both of them.

```html
<input x-model="q" />
<button @click="$action('search', { q }, { key: 'search', sync: 'replace' })">
  Search
</button>
<p hyper-loading-key="search">Searching...</p>
```

Different keys isolate concurrent work:

```html
<button @click="$action('save_profile', {}, { key: 'profile-save', sync: 'block' })">
  Save profile
</button>

<button @click="$action('upload_avatar', {}, { key: 'avatar-upload', sync: 'block' })">
  Upload avatar
</button>
```

### `onBeforeSubmit`

Use `onBeforeSubmit` to run client-side code immediately before the request is sent.

```html
<button
  @click="$action('save_profile', {}, {
    form: '#profile-form',
    onBeforeSubmit() {
      console.log('Submitting profile form');
    }
  })"
>
  Save
</button>
```

### `onUploadProgress`

Use `onUploadProgress` for file uploads or any request body where you want progress information.

```html
<button
  @click="$action('upload_avatar', {}, {
    form: '#avatar-form',
    method: 'POST',
    key: 'avatar-upload',
    onUploadProgress(detail) {
      console.log(detail.loaded, detail.total, detail.progress);
    }
  })"
>
  Upload avatar
</button>
```

## Outcomes

The Promise returned by `$action(...)` can resolve into different states.

`success`

```html
<button @click="$action('save_profile', {}, { form: '#profile-form' }).then(() => {
  console.log('Saved');
})">
  Save
</button>
```

`blocked`

```html
<button @click="$action('save_profile', {}, { form: '#profile-form', sync: 'block', key: 'profile-save' }).then((result) => {
  if (result && result.blocked) {
    console.log('Blocked');
  }
})">
  Save
</button>
```

`aborted`

```html
<button @click="$action('search', { q }, { sync: 'replace', key: 'search' }).then((result) => {
  if (result && result.aborted) {
    console.log('Replaced');
  }
})">
  Search
</button>
```

`rejected`

```html
<button @click="$action('upload_avatar', {}, { form: '#avatar-form', method: 'POST' }).catch((error) => {
  console.error(error);
})">
  Upload
</button>
```

## Runtime Events

HyperDjango emits browser events during the request lifecycle.

Common ones:

- `hyper:beforeRequest`
- `hyper:afterRequest`
- `hyper:requestBlocked`
- `hyper:requestReplaced`
- `hyper:requestAborted`
- `hyper:requestSuccess`
- `hyper:requestError`
- `hyper:requestException`
- `hyper:uploadProgress`
- `hyper:streamEvent`
- `hyper:toast`

```js
window.addEventListener("hyper:afterRequest", (event) => {
  console.log(event.detail.key, event.detail.ok, event.detail.aborted);
});
```

```js
window.addEventListener("hyper:uploadProgress", (event) => {
  if (event.detail.key !== "avatar-upload") {
    return;
  }
  console.log(event.detail.loaded, event.detail.total, event.detail.progress);
});
```

```js
window.addEventListener("hyper:streamEvent", (event) => {
  console.log(event.detail.event, event.detail.data);
});
```

## Server-Driven UI Options

In HyperDjango, UI behavior such as:

- target selector
- swap mode
- transition
- focus handling
- history push/replace

is expected to come from server-returned action items like `HTML(...)`, `Delete(...)`, `Redirect(...)`, and `History(...)`.

```python
from __future__ import annotations

from hyperdjango.actions import HTML, History


def build_result(results_html: str, q: str):
    return [
        HTML(
            content=results_html,
            target="#results",
            swap="inner",
            transition=True,
            focus="preserve",
        ),
        History(replace_url=f"/search/?q={q}"),
    ]
```
