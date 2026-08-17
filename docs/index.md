# HyperDjango Documentation

HyperDjango gives Django a server-first workflow with file routing, colocated assets, and hypermedia actions.

Use it when you want interactive UX without splitting your app into separate backend API and SPA frontend codebases.

## Current Release: 0.42.0

HyperDjango 0.42.0 keeps idle SSE action streams connected through proxies:

- generator streams emit standard `: heartbeat` SSE comments every 15 seconds while
  idle, across sync and async actions under WSGI and ASGI
- heartbeat comments stay transport-only: they do not dispatch application events,
  advance resume checkpoints, or change retry behavior
- `HYPER_SSE_HEARTBEAT_INTERVAL` controls the interval and accepts `0` to disable
  heartbeats

See the [SSE payload reference](reference/sse-payloads.md#heartbeat-comments) for the
wire contract and [settings reference](reference/settings.md#hyper_sse_heartbeat_interval)
for deployment configuration.

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
