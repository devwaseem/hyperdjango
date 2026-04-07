# Navigation Patterns Guide

`hyper-nav` is opt-in progressive navigation for links/forms.

Use it where partial page refresh improves UX, while keeping native browser behavior elsewhere.

## Basic Link Enhancement

```html
<a href="/todos" hyper-nav hyper-target="body">Todos</a>
```

Behavior:

- fetches destination
- swaps into `body`
- pushes browser history

## Enhanced GET Form

```html
<form method="get" action="/search" hyper-nav hyper-target="body">
  <input name="q" />
  <button type="submit">Search</button>
</form>
```

Behavior:

- serializes query string
- navigates with partial swap

## Excluding a Link

Use `hyper-no-nav` when a specific item must remain native.

```html
<a href="/export.csv" hyper-nav hyper-no-nav>Export</a>
```

## Back/Forward Target

Set popstate target once at page shell level:

```html
<body hyper-pop-target="body">
```

On back/forward, runtime re-fetches and swaps into this target.

## Sync for Navigation

Use sync attributes to avoid overlapping nav requests.

```html
<a href="/search?q=abc" hyper-nav hyper-sync="replace" hyper-key="main-nav">Search</a>
```
