# Troubleshooting

This guide shortens the feedback loop when integrating progressive interactions. It focuses on failure modes teams hit most often in production rollouts.

## Action returns full page on back/forward

Symptoms:

- popstate shows partial/action payload instead of full page shell
- page disappears or contains nested document markup after Back/Forward
- expected body scripts do not run after a restored page swap

Checks:

- ensure the restored URL renders a normal page for a plain `GET`
- ensure `hyper-pop-target` points at the element you intend to restore; if omitted, the runtime defaults to `body`
- ensure you are using Hyper action responses with no-cache headers
- verify reverse proxy/CDN is not caching action endpoints
- if restored scripts are required, keep them inside the returned `<body>` or load action-specific modules with `LoadJS(...)`

## Target swap does nothing

Symptoms:

- action succeeds but DOM is unchanged

Checks:

- confirm target selector exists at swap time
- ensure returned HTML is non-empty for swap modes that require HTML

## CSRF failures on POST actions/forms

Checks:

- keep Django CSRF middleware enabled
- include `{% csrf_token %}` in forms
- ensure CSRF cookie is present for authenticated pages
- if using CSP/meta-only flow, expose `meta[name='csrf-token']`

## View transition not visible

Checks:

- browser must support `document.startViewTransition`
- server response must set `transition: true`
- `hyper-view-transition-name` only labels transition parts; it does not enable transitions alone

## Duplicate or stale form fragments after swaps

Checks:

- keep IDs unique in replaced fragments
- prefer stable container target (for example `#profile-panel`) for `outer`/`inner` swaps
- avoid returning nested duplicate roots for the same target

## Route conflict error at startup

Checks:

- inspect `python manage.py hyper_routes`
- remove equivalent route shapes (for example `[slug]` and `[id]` in same path level)
- remove group-colliding paths (`(group)/x` vs `x`)

## `runserver` does not reload after editing `hyper/*`

Checks:

- ensure `hyperdjango` is in `INSTALLED_APPS`
- ensure `HYPER_FRONTEND_DIR` points to the directory you edit
- restart `runserver` once after changing settings
- verify you are using Django `runserver` autoreload (not a custom process manager without reload)

## HyperDjango Debug Toolbar is missing or stale

See the [HyperDjango Debug Toolbar guide](dev-toolbar.md) for middleware, URL,
static-asset, bounded-history, and SSE diagnostics.

Checks:

- confirm `HYPER_DEBUG_TOOLBAR=True`; it is independent of Django's `DEBUG` value
- register `hyperdjango.integrations.devtools` and its middleware
- mount `hyperdjango.integrations.devtools.urls` before broad file routes
- ensure `HYPER_DEBUG_TOOLBAR_CONFIG["URL_PREFIX"]` matches the mounted prefix
- when running with `DEBUG=False`, serve the packaged toolbar static assets through
  the application's normal production static-file path

## Django Debug Toolbar panel is missing or stale

See the [Django Debug Toolbar guide](debug-toolbar.md) for setup checks,
body-swap bridge requirements, fetch updates, Docker configuration, and SSE limitations.
