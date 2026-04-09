# Production Checklist

HyperDjango spans template rendering, runtime JS, and caching layers. Small config mismatches across these layers are a common source of release regressions.

## Runtime and App Settings

- Set `HYPER_FRONTEND_DIR` to your deployed frontend source directory.
- Set `HYPER_VITE_OUTPUT_DIR` to built static asset output.
- Set `HYPER_DEV = False` in production.
- Ensure collectstatic includes Vite output and `hyperdjango/static`.

See `docs/guides/vite-production-build.md` for full production build flow.

## Caching and Action Responses

Action responses include no-store/no-cache and `Vary` headers for Hyper request metadata.

- keep reverse proxies from overriding these headers on action endpoints
- avoid caching action JSON/partial responses in CDN edge caches

## Security

- keep Django CSRF middleware enabled
- send CSRF cookie or render `{% csrf_token %}` in base layout
- if using CSP, ensure nonce support for rendered asset tags

## Client Contracts

- use stable DOM IDs/selectors for `target` and OOB operations
- enable strict targets (`hyper-strict-targets`) in QA to catch selector drift
- define fallback behavior for missing JS (full-page paths should still work)

## Performance

- use `sync: "replace"` or explicit keys for rapid interactions (search, typeahead)
- use `hyper-loading-delay` to avoid flicker on fast requests
- prefer block rendering (`render_block`) for hot action paths

## Testing

- run routing checks in CI: `python manage.py hyper_routes`
- add tests for route conflict cases and action response contracts
- test back/forward navigation with enhanced links/forms
- verify 422 validation flows for form-driven `$action(..., {}, { form })` submits

## Deployment Validation

- start app with production settings and run key routes manually
- verify assets resolve from manifest (no Vite dev server URLs)
- verify toasts/signals/swaps on at least one action-heavy page
- verify target-not-found errors are absent in browser logs
