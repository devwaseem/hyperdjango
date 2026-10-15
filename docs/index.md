# HyperDjango Documentation

HyperDjango gives Django a server-first workflow with file routing, colocated assets, and hypermedia actions.

Use it when you want interactive UX without splitting your app into separate backend API and SPA frontend codebases.

## Current Release: 0.45.0

HyperDjango 0.45.0 keeps server-rendered navigation authoritative while making
it feel like an SPA:

- enhanced links and GET forms use browser Navigation API transitions when
  available, including native loading feedback
- Back and Forward always request the restored URL with `cache: "no-store"`
  and morph the server response instead of restoring a cached DOM snapshot
- full-page morphs preserve matching DOM identity, reconcile head assets, and
  reactivate appropriate body scripts
- the Request Inspector follows the active page trace across enhanced visits
  while ordinary actions preserve an explicit trace selection
- browser events now use a consistent colon-separated interface

See [History And Back/Forward Restoration](history.md), the
[Migration Guide](migration.md), and the
[Client Runtime Reference](reference/client-runtime.md) for the new contracts.

Existing projects must review the [0.45.0 migration guide](migration.md) for
the browser event renames. The [production checklist](production-checklist.md)
covers final deployment validation.

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
ai-quickstart
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
