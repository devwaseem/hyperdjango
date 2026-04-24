# HyperDjango Documentation

HyperDjango gives Django a server-first workflow with file routing, colocated assets, and hypermedia actions.

Use it when you want interactive UX without splitting your app into separate backend API and SPA frontend codebases.

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
actions
client-side-actions
declarative-html-apis
alpine-integration
assets-and-vite
cookbook
troubleshooting
production-checklist
faq
```

```{toctree}
:maxdepth: 1
:caption: Examples

examples/index
```
