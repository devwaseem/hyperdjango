# Troubleshooting

This guide shortens the feedback loop when integrating progressive interactions. It focuses on failure modes teams hit most often in production rollouts.

## Action returns full page on back/forward

Symptoms:

- popstate shows partial/action payload instead of full page shell

Checks:

- ensure you are using Hyper action responses with no-cache headers
- verify reverse proxy/CDN is not caching action endpoints

## Target swap does nothing

Symptoms:

- action succeeds but DOM is unchanged

Checks:

- confirm target selector exists at swap time
- enable strict mode (`hyper-strict-targets="true"`) to surface missing selectors
- ensure returned HTML is non-empty for swap modes that require HTML

## CSRF failures on POST actions/forms

Checks:

- keep Django CSRF middleware enabled
- include `{% csrf_token %}` in forms
- ensure CSRF cookie is present for authenticated pages
- if using CSP/meta-only flow, expose `meta[name='csrf-token']`

## `hyper-nav` not triggering

Checks:

- `hyper-nav` is opt-in; add it to link/form
- ensure element does not include `hyper-no-nav`
- external URLs, downloads, and modified-clicks intentionally bypass enhancement

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
