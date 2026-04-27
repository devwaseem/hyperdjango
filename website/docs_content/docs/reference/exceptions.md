# Exceptions Reference

HyperDjango utilizes custom exceptions to signal framework-level errors.

| Exception | Raised In | Trigger |
| :--- | :--- | :--- |
| `FileNotLoadedFromViteError` | `hyperdjango.page` | Requested file not found in Vite manifest. |
| `DispatchError` | `hyperdjango.runtime.dispatcher`| Invalid method, missing action, or bad return type. |
| `RouteLoadError` | `hyperdjango.routing.loader` | Route file cannot be loaded or invalid structure. |
| `PageContextNotFoundError` | `hyperdjango.templatetags` | Template tag missing `page` in context. |

All exceptions inherit directly from the Python built-in `Exception`.

## Detailed Trigger Conditions

### `FileNotLoadedFromViteError`
Raised when attempting to resolve a JS/TS import or template that exists on disk but was not processed during the Vite build phase. Ensure the file is included in your Vite entry points.

### `DispatchError`
Occurs during the action dispatch lifecycle:
- Request method not supported by the page.
- Action method not defined on the `PageView`.
- Action returned an unsupported type.
- Page handler returned an unsupported type.

### `RouteLoadError`
Occurs during the initial scanning of the routes directory:
- `+page.py` exists but cannot be imported.
- No `PageView` class found in the module.
- `PageView` does not inherit from `HyperView` or `HyperPageTemplate` correctly.

### `PageContextNotFoundError`
Raised if you attempt to use HyperDjango template tags (like `{% render_block ... %}`) outside of a context managed by a HyperDjango route.
