# Assets and Vite

HyperDjango is built around automatic asset discovery.

Pages, layouts, and template packages can load nearby Vite entries without hand-wiring script tags for every feature.

## Core Settings

```python
HYPER_FRONTEND_DIR = BASE_DIR / "hyper"
HYPER_VITE_OUTPUT_DIR = BASE_DIR / "dist"
HYPER_VITE_DEV_SERVER_URL = "http://localhost:5173/"
HYPER_DEV = DEBUG

TEMPLATES[0]["DIRS"].append(HYPER_FRONTEND_DIR)
STATICFILES_DIRS = [HYPER_VITE_OUTPUT_DIR]
```

### `HYPER_FRONTEND_DIR`

Where HyperDjango finds your `hyper/` tree.

### `HYPER_VITE_OUTPUT_DIR`

Where Vite writes built assets. In production, HyperDjango reads the manifest here.

### `HYPER_VITE_DEV_SERVER_URL`

Which Vite dev server URL should be injected during development.

### `HYPER_DEV`

Whether to use dev-server assets or manifest-based production assets.

## Automatic Entry Discovery

HyperDjango looks for nearby files such as:

- `entry.ts`
- `entry.js`
- `entry.head.ts`
- `entry.head.js`
- custom entries like `admin.entry.ts`

This works for:

- routed pages
- layout packages
- standalone template packages

## What Gets Loaded

- `entry.ts` / `entry.js`: body module scripts
- `entry.head.ts` / `entry.head.js`: head module scripts
- CSS imported by those entries
- Vite module preloads

## Development vs Production

In development:

- HyperDjango injects the Vite dev server URL
- Vite client is added automatically where needed

In production:

- HyperDjango resolves built assets from `dist/.vite/manifest.json`

## Template Tags

Load the tags:

```django
{% load hyper_tags %}
```

Available tags:

- `{% hyper_preloads %}`
- `{% hyper_stylesheets %}`
- `{% hyper_head_scripts %}`
- `{% hyper_body_scripts %}`
- `{% hyper_custom_entry "admin" %}`

These tags read asset information from the current `page` object in template context.
