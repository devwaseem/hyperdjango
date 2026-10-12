# HyperDjango Documentation

HyperDjango gives Django a server-first workflow with file routing, colocated assets, and hypermedia actions.

Use it when you want interactive UX without splitting your app into separate backend API and SPA frontend codebases.

## Current Release: 0.44.0

HyperDjango 0.44.0 makes framework conventions discoverable and action
failures precise:

- a bundled Agent Skills-compatible guide teaches file routes, colocated Vite
  entries, layouts, and typed actions
- `hyper_scaffold --agent-skill` installs that guide directly into a project
- the new AI quickstart and concise `/llms.txt` index give coding agents a
  reliable entry point without loading the complete documentation corpus
- action arguments are validated before invocation, so missing or unexpected
  request and route names produce an actionable `400` instead of an opaque
  `500`
- the root README now takes a project from installation through its first
  routed page, colocated asset, action, and production deployment

See [AI Quickstart](ai-quickstart.md), [Actions](actions.md), and
[Getting Started](installation.md) for the new contracts.

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
