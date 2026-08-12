# Example App

The repository includes a complete example project under `example/`.

What it demonstrates:

- file routing (`index`, static, dynamic, catch-all, route groups)
- nested reusable layouts (`/dashboard`, `/dashboard/settings`)
- action-driven swaps and multi-target HTML updates (`/todos`)
- local and global signals (`/signals`)
- composite segment matching (`/account/reset/<uidb36>-<key>`)
- literal+param regex segment (`/regex/<kind>-v<version>`)
- typed dynamic segment (`/typed/<str:slug>`)
- inline regex token segment (`/regex-inline/<uidb36>-<key>`)
- template package rendered by custom Django view (`/template-card`)
- file-routed `PageView` subclassing plain `django.views.View` (`/plain-django-view`)
- sync behavior for live interactions (`/search`)
- Django form enhancement with `$action(..., {}, { form })` (`/profile`)
- named-checkpoint resumable SSE streams and a non-retried-by-default `POST` command →
  `switch_to()` → retryable-by-default read-only `GET` watcher workflow (`/sse-demo`)

Run steps are documented in the example project's README under `example/`.

The project website also includes a [live command-to-query demo](/#switch-action-demo).
It intentionally interrupts the read-only watcher and exposes its reconnect state,
latest acknowledged checkpoint, separate request IDs, continuous loading lifecycle, and
one-time command execution in the page.
