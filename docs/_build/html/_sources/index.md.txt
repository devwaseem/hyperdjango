# HyperDjango Documentation

HyperDjango gives Django a server-first workflow with file routing, page classes, and progressive hypermedia interactions.

Use it when you want interactive UX without splitting your app into separate backend API and SPA frontend codebases.

## Problem -> Approach -> Outcome

- Problem: feature logic drifts across templates, API endpoints, and frontend state code.
- Approach: keep routes, templates, actions, and assets together under `hyper/`.
- Outcome: faster feature work, simpler architecture, and SPA-like interactions from server-rendered pages.

## Locality of Behavior

HyperDjango keeps feature code co-located in one `hyper/` tree:

```text
hyper/
  layouts/
    base/
      index.html
      entry.ts
  routes/
    profile/
      page.py
      index.html
      partials/
        form.html
        success.html
  shared/
```

Route behavior lives together:

- `page.py`: request handlers and actions
- `index.html`: full page rendering
- `partials/*`: action fragments
- `entry.ts`: client behavior scoped to layout/route

The docs are organized into three sections:

- **Guides**: feature explanations, installation, and production usage
- **Reference**: precise behavior of settings, events, and runtime attributes
- **Examples / Cookbook**: practical patterns and copy-paste recipes

```{toctree}
:maxdepth: 2
:caption: Guides

guides/index
```

```{toctree}
:maxdepth: 2
:caption: Reference

reference/index
```

```{toctree}
:maxdepth: 2
:caption: Examples

examples/index
```
