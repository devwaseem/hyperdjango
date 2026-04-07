# Config Reference

These settings and attributes exist to keep server rendering as the default while still enabling progressive client behavior where needed. Most options are explicit so you can opt into behavior per page or per interaction.

## Django Settings

### `HYPER_FRONTEND_DIR`

- type: `Path | str`
- required: yes
- purpose: root directory containing `routes/`, `layouts/`, shared templates/assets

Example:

```python
HYPER_FRONTEND_DIR = BASE_DIR / "hyper"
```

In development, this directory is also used for `runserver` autoreload file watching.

### `HYPER_VITE_OUTPUT_DIR`

- type: `Path | str`
- required: yes
- purpose: Vite build output (`manifest.json` + built assets)

Example:

```python
HYPER_VITE_OUTPUT_DIR = BASE_DIR / "dist"
```

### `HYPER_VITE_DEV_SERVER_URL`

- type: `str`
- required: no (default `http://localhost:5173/`)
- purpose: dev-time asset URL base

### `HYPER_DEV`

- type: `bool`
- required: no
- fallback: `DEBUG`
- purpose: controls dev asset behavior (including Vite client injection)

## Template Requirements

- add `HYPER_FRONTEND_DIR` to `TEMPLATES[0]["DIRS"]`
- include HyperDjango tags in base templates where page assets should render

```django
{% load hyper_tags %}
```

## Base Template Behavior

The shipped base template (`hyperdjango/templates/hyperdjango/base.html`) provides:

- page title fallback
- asset tag rendering hooks
- hidden CSRF token mount
- runtime script include
- optional default swap/settle CSS classes

You can replace it with your own base template. See `docs/guides/custom-base-template.md` for the required hooks.

## HTML Attributes (Runtime)

### Navigation

- `hyper-nav`: opt-in nav enhancement for links/forms
- `hyper-no-nav`: hard-disable enhancement on an element (takes precedence over `hyper-nav`)
- `hyper-target`: target selector for enhanced nav swaps (default `body`)
- `hyper-pop-target` (on `body`): popstate target selector

### Requests / Sync

- `hyper-sync`: `replace|block|none`
- `hyper-key`: request sync key
- `hyper-strict-targets`: strict target mode on element/form

### Loading

- `hyper-loading`
- `hyper-loading-delay`
- `hyper-loading-action`
- `hyper-loading-key`
- `hyper-loading-disable`
- `hyper-loading-disable-key`
- `hyper-target-busy`

### Forms

- `hyper-form`
- `hyper-form-disable`
- `hyper-action`
- `hyper-swap`
- `hyper-focus`
- `hyper-transition`
- `hyper-swap-delay`
- `hyper-settle-delay`

### View Transitions

- `hyper-view-name`: mapped to CSS `view-transition-name`
