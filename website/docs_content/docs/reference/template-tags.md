# Template Tags

Load tags:

```django
{% load hyper_tags %}
```

Available tags:

- `{% hyper_preloads %}`
- `{% hyper_stylesheets %}`
- `{% hyper_head_scripts %}`
- `{% hyper_body_scripts %}`
- `{% hyper_custom_entry "admin" %}`

These read asset information from the current `page` object.

If `page` is missing from template context, HyperDjango raises `PageContextNotFoundError`.

## `hyper_preloads`

Renders module preload tags collected from the current page and its inherited templates/layouts.

Source:

- `page.preload_imports`

## `hyper_stylesheets`

Renders stylesheet tags collected from Vite entry imports.

Source:

- `page.stylesheets`

Nonce behavior:

- if `request._csp_nonce` exists, the nonce is attached to the rendered tags

## `hyper_head_scripts`

Renders module scripts discovered from `entry.head.js` or `entry.head.ts`.

Source:

- `page.head_imports`

## `hyper_body_scripts`

Renders module scripts discovered from `entry.js` or `entry.ts`.

Source:

- `page.body_imports`

## `hyper_custom_entry "name"`

Looks for:

- `name.entry.js`
- `name.entry.ts`

If neither exists, HyperDjango raises `FileNotFoundError`.

Resolution order:

1. `name.entry.js`
2. `name.entry.ts`
