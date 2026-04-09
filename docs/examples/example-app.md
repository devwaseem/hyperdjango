# Example App

The repository includes a complete example project under `example/`.

What it demonstrates:

- file routing (`index`, static, dynamic, catch-all, route groups)
- nested layouts (`/dashboard`, `/dashboard/settings`)
- action-driven swaps and OOB updates (`/todos`)
- local and global signals (`/signals`)
- composite segment matching (`/account/reset/<uidb36>-<key>`)
- literal+param regex segment (`/regex/<kind>-v<version>`)
- typed dynamic segment (`/typed/<str:slug>`)
- inline regex token segment (`/regex-inline/<uidb36>-<key>`)
- template package rendered by custom Django view (`/template-card`)
- file-routed `PageView` subclassing plain `django.views.View` (`/plain-django-view`)
- sync behavior for live interactions (`/search`)
- Django form enhancement with `$action(..., {}, { form })` (`/profile`)

Run steps are documented in `example/README.md`.
