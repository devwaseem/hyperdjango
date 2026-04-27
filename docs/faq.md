# FAQ

## Is Alpine required?

No. HyperDjango works with plain JavaScript through `hyper.js`.

Alpine is recommended because it gives you `$action(...)` and direct signal integration.

## Should I start with `HyperView` or plain Django `View`?

Start with `HyperView` unless you only want file-based routing.

Use plain `View` when routing is the only HyperDjango feature you need for that page.

## Where should layouts live?

Put layouts in `hyper/layouts/...` and inherit them explicitly from `PageView` classes.

## When should I use `render()` vs `render_template()`?

Use `render()` for page-local templates such as `partials/form.html`.

Use `render_template()` for directory-based partial units with `index.html` and optional `entry.ts`.

## Should actions return lists or generators?

Use a list when the whole response is known immediately.

Use a generator when action items should be streamed over time.

## What does `key` do?

`key` creates a named request coordination lane.

It affects:

- `sync`
- loading indicators
- disable states
- upload progress correlation

## Where should target, swap, transition, and history behavior live?

Prefer to define those on the server through typed action items such as `HTML(...)`, `Delete(...)`, `Redirect(...)`, and `History(...)`.
