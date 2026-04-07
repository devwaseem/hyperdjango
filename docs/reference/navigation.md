# Navigation Reference

## `hyper-nav`

Enables fetch-and-swap navigation for links and forms.

- default behavior is opt-in
- links/forms without `hyper-nav` remain native browser navigation

Example:

```html
<a href="/todos" hyper-nav hyper-target="body">Todos</a>
```

## `hyper-no-nav`

Disables Hyper navigation on a specific element.

- takes precedence over `hyper-nav`
- useful for downloads, exports, or routes you always want fully native

Example:

```html
<a href="/export.csv" hyper-nav hyper-no-nav>Export</a>
```

## `hyper-target`

Sets the target selector used by nav swaps.

- default: `body`

Example:

```html
<a href="/search" hyper-nav hyper-target="#main">Search</a>
```

## `hyper-pop-target`

Sets target selector for back/forward (`popstate`) fetch-and-swap.

- usually placed on `body`
- default when missing: `body`

Example:

```html
<body hyper-pop-target="body">
```

## Related Attributes

Navigation requests also honor:

- `hyper-sync`
- `hyper-key`
- `hyper-transition`
- `hyper-swap-delay`
- `hyper-settle-delay`
- `hyper-focus`
