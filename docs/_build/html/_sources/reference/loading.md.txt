# Loading Reference

## `hyper-loading`

Shows/hides an element based on request activity.

Scopes:

- global: `hyper-loading`
- key-scoped: `hyper-loading="search-key"` or `hyper-loading-key="search-key"`
- action-scoped: `hyper-loading-action="search"`

Examples:

```html
<div hyper-loading>Loading...</div>
<div hyper-loading="live-search">Searching...</div>
<div hyper-loading-action="search">Searching...</div>
```

## `hyper-loading-delay`

Delays indicator visibility to reduce flicker on fast requests.

Value:

- integer milliseconds

Example:

```html
<div hyper-loading hyper-loading-delay="150">Loading...</div>
```

## `hyper-loading-disable`

Disables controls while requests are active.

Scopes:

- global: `hyper-loading-disable`
- key-scoped: `hyper-loading-disable="search-key"` or `hyper-loading-disable-key="search-key"`

Examples:

```html
<button hyper-loading-disable>Save</button>
<button hyper-loading-disable="live-search">Search</button>
```

## `hyper-target-busy`

Mirrors `aria-busy` state for a target selector.

Example:

```html
<section hyper-target-busy="#results"></section>
```

## Global Busy Behavior

The runtime also updates:

- `<html hyper-loading>` while requests are pending
- `aria-busy` on `<html>` and `<body>`
