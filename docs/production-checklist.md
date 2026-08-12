# Production Checklist

HyperDjango spans template rendering, runtime JS, and caching layers. Small config mismatches across these layers are a common source of release regressions.

## Runtime and App Settings

- Set `HYPER_FRONTEND_DIR` to your deployed frontend source directory.
- Set `HYPER_VITE_OUTPUT_DIR` to built static asset output.
- Set `HYPER_DEV = False` in production.
- Ensure collectstatic includes Vite output and `hyperdjango/static`.

See the Assets and Vite page for the main asset build and manifest flow.

## Caching and Action Responses

Action responses include no-store/no-cache and `Vary` headers for Hyper request metadata.

- keep reverse proxies from overriding these headers on action endpoints
- avoid caching action JSON/partial responses in CDN edge caches
- preserve `X-Hyper-Request-ID`, `Last-Event-ID`, and `X-Hyper-Switch-Depth`

For command-to-query handoffs, verify the originating mutation uses POST (which does not
retry by default), commits durable state before returning `action.switch_to(...)`, and
can be recovered by refresh if the response is lost. Audit GET destination watchers as
genuinely side-effect-free and test their named-checkpoint or idempotent
replacement-patch contract under reconnection. The switch payload must not carry retry;
the client recomputes the destination default from its method. Set
`HYPER_SWITCH_ACTION_MAX_DEPTH` only if the default four-switch loop bound is too small.

## Security

- keep Django CSRF middleware enabled
- send CSRF cookie or render `{% csrf_token %}` in base layout
- treat `X-Hyper-Request-ID` and `Last-Event-ID` as untrusted progress metadata; never
  let a resume checkpoint bypass authentication, authorization, tenant, or resource
  validation
- if using CSP, use Django's CSP middleware/context processor or otherwise
  expose `request._csp_nonce` so HyperDjango can nonce rendered asset tags,
  runtime scripts, and dynamically activated scripts
- if `HYPER_DEBUG_TOOLBAR=True`, confirm that exposing sanitized traces, SQL,
  request metadata, replay, pause, and clear controls is intentional and protected by
  the deployment's access policy; otherwise disable it

## Client Contracts

- use stable DOM IDs/selectors for server-targeted HTML and delete patches
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
- for every command-to-query handoff, interrupt the watcher in an E2E test and assert:
  the command was sent once, the watcher reconnected with a distinct command/watcher
  request ID pair, only the watcher reused its own request ID and named
  `Last-Event-ID`, and keyed loading remained active until the final watcher completed
- for each checkpointed GET stream, interrupt after every marker and assert that only
  later stages execute; also verify stale, malformed, and cross-request cursors restart
  safely
- confirm GET actions retry by default, POST actions do not, and any POST that explicitly
  sets `retry: true` deduplicates side effects in shared durable storage
- test configured switch-depth rejection and external abort/replacement of the complete
  chain when an application uses multi-switch workflows

## Deployment Validation

- start app with production settings and run key routes manually
- verify assets resolve from manifest (no Vite dev server URLs)
- verify toasts/signals/swaps on at least one action-heavy page
- verify target-not-found errors are absent in browser logs
