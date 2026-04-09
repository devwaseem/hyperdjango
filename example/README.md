# HyperDjango Example

This example is an end-to-end Django app wired to `hyperdjango`.

Action responses in the example now use the typed item style (`Signal`, `HTML`, `Toast`, etc.), which HyperDjango streams to the browser as SSE-framed events.

## Feature Coverage

- file routing (`index`, static, dynamic, catch-all, route groups)
- nested layouts (`/dashboard`, `/dashboard/settings`)
- action-driven partial updates (`/`, `/todos`, `/search`)
- OOB updates and toasts (`/todos`)
- sync lanes and request lifecycle behavior (`/search`)
- Django form enhancement via `$action(..., data, { form })` (`/profile`)

## Route Map

- `/` -> `hyper/routes/index/+page.py`
- `/about` -> `hyper/routes/about/+page.py`
- `/blog/<slug>` -> `hyper/routes/blog/[slug]/+page.py`
- `/docs/<path:path>` -> `hyper/routes/docs/[...path]/+page.py`
- `/account/reset/<uidb36>-<key>` -> `hyper/routes/account/reset/[uidb36]-[key]/+page.py`
- `/regex/<kind>-v<version>` -> `hyper/routes/regex/[kind]-v[version]/+page.py`
- `/typed/<str:slug>` -> `hyper/routes/typed/[str__slug]/+page.py`
- `/regex-inline/<uidb36>-<key>` -> `hyper/routes/regex-inline/[uidb36__[0-9A-Za-z]+]-[key__.+]/+page.py`
- `/pricing` -> `hyper/routes/(marketing)/pricing/+page.py`
- `/dashboard` -> `hyper/routes/dashboard/index/+page.py`
- `/dashboard/settings` -> `hyper/routes/dashboard/settings/+page.py`
- `/modal-demo` -> `hyper/routes/modal-demo/+page.py`
- `/upload-progress` -> `hyper/routes/upload-progress/+page.py`
- `/sse-demo` -> `hyper/routes/sse-demo/+page.py`
- `/search` -> `hyper/routes/search/+page.py`
- `/todos` -> `hyper/routes/todos/+page.py`
- `/signals` -> `hyper/routes/signals/+page.py`
- `/profile` -> `hyper/routes/profile/+page.py`
- `/template-card` -> custom URL + `hyper/templates/profile_card/page.py`
- `/plain-django-view` -> `hyper/routes/plain-django-view/+page.py` (`django.views.View`)

`/modal-demo` demonstrates `HyperPageTemplate.render_template(...)` rendering a directory-relative partial package with its own `entry.ts`, then returning it as typed `HTML` + `LoadJS` items.

`/upload-progress` demonstrates upload progress tracking with both Alpine `$action(...)` + `hyper:uploadProgress` and plain `window.action(...)` + `onUploadProgress`.

`/sse-demo` demonstrates a long-running action yielding incremental typed items, streamed to the browser as live SSE-framed updates.

Most example actions now return typed items (`Signal`, `HTML`, `Toast`, `LoadJS`, etc.), which HyperDjango streams to the browser as SSE-framed action events.

## Run

From repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Then run Vite and Django in separate terminals.

Terminal 1:

```bash
cd example
npm install
npm run dev
```

Terminal 2:

```bash
cd example
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Verification Checklist

1. `python manage.py hyper_routes` lists all routes above.
2. `/` increment action updates without full reload.
3. `/search` cancels/replaces in-flight requests on repeated queries.
4. `/todos` supports add/toggle/delete with partial swaps + OOB updates.
5. `/signals` demonstrates `count` (local) vs `$count` (global store) patching.
6. `/profile` returns server-rendered validation errors and success partials.
7. `/upload-progress` shows progress updates for file uploads in both callback and event-driven styles.
8. `/sse-demo` shows a long-running streamed action updating progress and appending live server log entries.
9. `/template-card` renders a `HyperPageTemplate` from a custom Django view (no file route).
10. `/plain-django-view` demonstrates file route resolution with plain `django.views.View`.
11. `/account/reset/abc123-token456` resolves both `uidb36` and `key` from one segment.
12. `/regex/release-v42` demonstrates literal + params composite regex matching.
13. `/typed/hello-world` demonstrates typed dynamic token syntax.
14. `/regex-inline/A1b2c3-reset-token-xyz` demonstrates inline regex token syntax.
