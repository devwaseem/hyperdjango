# HyperDjango Documentation

HyperDjango gives Django a server-first workflow with file routing, colocated assets, and hypermedia actions.

Use it when you want interactive UX without splitting your app into separate backend API and SPA frontend codebases.

## Current Release: 0.43.0

HyperDjango 0.43.0 deepens full-page navigation and DOM continuity while
keeping interactions action-first:

- full-document visits reconcile route-specific head assets before committing
  the body
- `hyper-preserve`, explicit morph/replace strategies, and `hyper-select`
  protect stateful DOM and support progressive enhancement
- viewport-triggered fragments call read-only page actions instead of
  introducing fragment-only URLs
- resumable GET streams can pause in hidden tabs, and Alpine signals can
  initialize missing state without overwriting existing values
- production Vite output exposes only flattened public assets while keeping
  the manifest and source tree private

See [History And Back/Forward Restoration](history.md), [Actions](actions.md),
and [Declarative HTML APIs](declarative-html-apis.md) for the new contracts.

Existing projects should also review the [0.38.0 project upgrade notes](https://github.com/devwaseem/hyperdjango/blob/main/CHANGELOG.md#project-upgrade-notes), especially the Vite 8 and Node.js requirements. The [production checklist](production-checklist.md) covers the final validation steps.

## Core Ideas

- file-based routing for Django pages
- automatic asset loading for pages, layouts, and template packages
- hypermedia actions that return HTML, events, redirects, history updates, and small client patches

## Relationship to Alpine

HyperDjango works without Alpine, but Alpine is the client-side library it integrates with most closely.

- HyperDjango core: works with plain JavaScript through `hyper.js`
- Alpine integration: recommended layer for `$action(...)` and signal patching

## Documentation Map

The docs are split by concept ownership:

- start with getting a page working
- then learn routing, rendering, layouts, and actions
- then learn client-side invocation and declarative HTML APIs
- use the reference section for exact runtime details

```{toctree}
:maxdepth: 1
:caption: Guides

installation
routing
pages-and-rendering
layouts
base-template
actions
history
client-side-actions
declarative-html-apis
alpine-integration
assets-and-vite
dev-toolbar
debug-toolbar
troubleshooting
production-checklist
faq
```

```{toctree}
:maxdepth: 1
:caption: Reference

reference/index
```

```{toctree}
:maxdepth: 1
:caption: Examples

examples/index
```
