# HyperDjango Documentation

HyperDjango gives Django a server-first workflow with file routing, colocated assets, and hypermedia actions.

Use it when you want interactive UX without splitting your app into separate backend API and SPA frontend codebases.

## Current Release: 0.40.1

HyperDjango 0.40.1 makes the standalone Request Inspector quieter and more focused:

- keep the inspector hidden until the DOM, stylesheet, and initial trace state are ready
- set `HYPER_DEBUG_TOOLBAR_CONFIG["RECORD_PAGE_REQUESTS"] = False` to retain only
  Hyper action requests while keeping the launcher available on HTML pages
- exclude Django Debug Toolbar's internal polling endpoints from HyperDjango capture
  even when DJDT is mounted under a custom path
- restore a previously open inspector immediately on refresh without replaying the
  drawer animation

See the [Request Inspector guide](dev-toolbar.md) for configuration and behavior. The
0.39 command-to-query handoff remains documented under
[`action.switch_to(...)`](actions.md#command-to-query-handoff-with-switch_to).

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
