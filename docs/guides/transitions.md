# Transitions Guide

HyperDjango supports two transition layers:

- swap lifecycle classes (`hyper-swapping`, `hyper-settling`)
- browser View Transitions API (`transition: true`)

## Swap Lifecycle Classes

During mutation, target receives:

1. `hyper-swapping`
2. `hyper-settling`

This lets you attach simple CSS transitions without extra JS.

Example:

```css
.hyper-swapping { opacity: 0.92; }
.hyper-settling { animation: settle 160ms ease-out; }
```

## View Transitions

Enable from the server response:

```python
return self.action_response(..., transition=True)
```

## Naming Transition Regions

Use `hyper-view-transition-name` to map elements to `view-transition-name`.

```html
<section hyper-view-transition-name="profile-panel"></section>
```

`hyper-view-name` is still accepted as a backward-compatible alias.

This controls transition pairing; it does not enable transitions by itself.

## Timing Controls

Client options:

- `swapDelay`
- `settleDelay`

Server options:

- `swap_delay`
- `settle_delay`

Use delays for choreographing staged updates.
