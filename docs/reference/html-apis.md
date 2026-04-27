# HTML Loading and UI APIs

HyperDjango provides declarative HTML attributes to manage UI states and transitions during action requests.

## Loading Attributes

These attributes allow you to modify elements based on pending action requests.

### `hyper-loading`
- **Behavior**: Toggles element visibility (`hidden` attribute).
- **Scope**: Matches active requests. If a request is active, the element becomes visible (`hidden=false`).

### `hyper-loading-disable`
- **Behavior**: Toggles the `disabled` property on form elements (`button`, `input`).
- **Scope**: If a request is active, the element is disabled (`disabled=true`). Restores original state when the request completes.

### `hyper-loading-class`
- **Behavior**: Toggles a CSS class based on active requests.
- **Scope**: Adds the specified class(es) when active, removes them when inactive.

### `hyper-loading-remove-class`
- **Behavior**: The inverse of `hyper-loading-class`.
- **Scope**: Removes the specified class(es) when active, adds them when inactive.

### `hyper-loading-delay`
- **Behavior**: Adds a debounce delay (in milliseconds) before applying visibility changes for `hyper-loading` elements.
- **Purpose**: Prevents UI flicker for very fast requests.

### `hyper-target-busy`
- **Behavior**: Adds `aria-busy="true"` to a target element when the associated action is active.

### Scoping Attributes

These attributes refine which requests trigger the loading state on the element.

| Attribute | Purpose |
| :--- | :--- |
| `hyper-loading-key` | Links the element to requests with a specific coordination `key`. |
| `hyper-loading-action`| Links the element to requests for a specific action name. |
| `hyper-loading="key"` | Shorthand for applying loading state to a specific request key. |
| `hyper-loading-disable-key` | Links `hyper-loading-disable` to a specific key. |
| `hyper-loading-disable="key"` | Shorthand for disabling based on a specific key. |

If no scoping attribute is provided, the element tracks **global** request state.

## UI Management Attributes

### `hyper-form-disable`
- **Behavior**: Applied to a `<form>` element. Automatically adds `hyper-loading-disable` to all `<button>`, `input[type="submit"]`, and `input[type="button"]` controls within the form when a request is active.
- **Purpose**: Provides a declarative way to disable all form controls during submission without adding individual attributes to every button.

### `hyper-view-transition-name`
- **Behavior**: Sets the CSS `view-transition-name` property on the element to the provided value.
- **Purpose**: Enables the browser's View Transitions API for this element. When a `transition=True` flag is passed in an `HTML` action, the runtime uses these transition names to coordinate smooth animations between DOM updates.
- **Note**: Ensure the transition name is unique within the document.

## Guidance

- Use `hyper-loading-key` when the request lane is already named with `$action(..., { key })`.
- Use `hyper-loading-action` when you care about one action name regardless of key.
- Use `hyper-loading-disable*` when controls should stop duplicate input during active requests.

