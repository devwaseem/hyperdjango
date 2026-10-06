# Hypermedia Framework Opportunities

Research date: 2026-10-06

## Executive recommendation

HyperDjango already implements most of the high-value transport ideas associated with
HTMX and Datastar: typed multi-target results, SSE delivery, request synchronization,
bounded reconnects, offline-aware retries, explicit resume checkpoints, history updates,
server-selected swaps, focus handling, view transitions, loading state, and unusually
strong request/SSE inspection.

The best next work is therefore not another transport or reactive language. It is to make
full-document navigation and DOM continuity more complete:

1. reconcile `<head>` assets during enhanced navigation;
2. add an explicit persistent-element contract and morph strategy;
3. select fragments from full-page responses for progressive enhancement;
4. optionally suspend resumable GET streams while a tab is hidden;
5. add conservative lazy fragment loading;
6. allow signal initialization without overwriting existing client state.

## Ranked opportunities

### 1. Reconcile `<head>` assets during navigation — priority 5/5

**Current gap.** HyperDjango discovers route-, layout-, and template-specific Vite assets
in `hyperdjango/page.py` and `hyperdjango/assets/resolver.py`. Enhanced full-document
responses are normalized in `hyperdjango/static/hyperdjango/hyper.js`, but the current
normalization only updates `document.title`, body attributes, body HTML, and body scripts.
It does not reconcile route-specific stylesheets, module preloads, or head scripts.

This means navigation between pages with different head entries can leave the destination
without its CSS or head module, or leave stale route CSS active. That should be covered by
a browser regression before implementation.

**Proposed contract.**

- Parse the returned `<head>` for body-targeted enhanced navigation and history restore.
- Identify external assets by normalized `href` or `src` and stable metadata by a
  deterministic key.
- Add and load new styles/scripts before committing the body swap.
- Keep unchanged assets without re-evaluating scripts.
- Remove route-scoped assets absent from the destination only after the new body settles.
- Support `hyper-head="merge|append|ignore"` and `hyper-preserve` for explicitly permanent
  entries.
- Preserve CSP nonces and expose added/kept/removed asset records to the existing inspector.

HTMX 4's `hx-head` extension defines append/merge semantics and lifecycle hooks, while
Turbo Drive has long appended new head scripts and uses fingerprinted asset URLs. HTMX 4
is recent, so its exact API should be treated as evidence for the problem rather than
copied wholesale.

Sources:

- [HTMX 4 `hx-head`](https://four.htmx.org/extensions/hx-head)
- [HTMX 4.0.0 release](https://github.com/bigskysoftware/htmx/releases/tag/v4.0.0)
- [Turbo: working with script elements](https://turbo.hotwired.dev/handbook/building#working-with-script-elements)

### 2. Persistent DOM islands plus an explicit morph strategy — priority 5/5

**Current gap.** HyperDjango automatically uses Alpine Morph or `morphdom` for `inner`
and `outer` swaps when either global is present, then falls back to replacement. There is
no public persistence marker or explicit way to select the patch strategy, so behavior
depends on the application's installed globals. Stateful elements such as video players,
editors, canvases, custom elements, and third-party widgets can still be destroyed by an
ancestor swap.

**Proposed contract.**

- Add `hyper-preserve` for elements with stable IDs.
- Match preserved nodes by ID and move the existing node into the incoming tree.
- Keep position (`swap="inner|outer|..."`) separate from strategy, for example
  `HTML(..., swap="outer", strategy="morph")`, with an explicit replacement option.
- Define lifecycle events for preserved, added, updated, and removed nodes.
- Keep strict-target checks and duplicate-ID diagnostics active.
- Start with one supported morph adapter and a small registry; do not expose arbitrary
  runtime internals as a general plugin API.

HTMX's `hx-preserve`, Turbo's `data-turbo-permanent`, and Datastar's
`data-ignore-morph` independently establish the value of an explicit persistence
boundary. Morphing should remain opt-in because it trades DOM continuity for CPU cost and
can interact badly with widgets that own their subtree.

Sources:

- [HTMX `hx-preserve`](https://htmx.org/attributes/hx-preserve/)
- [HTMX morphing guidance](https://htmx.org/docs/#morphing)
- [Turbo permanent elements](https://turbo.hotwired.dev/handbook/building#persisting-elements-across-page-loads)
- [Datastar attributes reference](https://data-star.dev/reference/attributes)

### 3. Select a response fragment from a full-page response — priority 4/5

**Current gap.** HyperDjango can target a narrow element, but callers must ensure the
response itself is already markup appropriate for that target. A normal route response
cannot be reused cleanly when an enhanced link wants only `#main` from the returned full
document.

**Proposed contract.**

```html
<a href="/account/" hyper-nav hyper-target="#main" hyper-select="#main">
  Account
</a>
```

The request remains an ordinary full-page GET. With JavaScript disabled, the browser
navigates normally. With HyperDjango active, the runtime parses the response, selects the
requested fragment, and swaps it into the target. Missing or ambiguous response selectors
must fail under strict-target mode and appear in inspector diagnostics.

This avoids maintaining separate full-page and partial rendering paths. It follows the
mature `hx-select` behavior without adopting HTMX's entire response-header protocol.

Source:

- [HTMX `hx-select`](https://htmx.org/attributes/hx-select/)

### 4. Suspend resumable GET streams in hidden tabs — priority 4/5

**Current gap.** HyperDjango pauses retries while offline but does not react to
`visibilitychange`. Long-running read-only streams therefore keep connections and server
work active while a tab is hidden.

**Proposed contract.**

- Add a client option such as `pauseWhenHidden: true` for GET actions.
- Abort the connection on hide without marking the request lane as failed.
- Resume on visibility using the same request ID and latest acknowledged checkpoint.
- Emit explicit pause/resume lifecycle events for the inspector.
- Keep the initial default `false`. Without a checkpoint, reconnection restarts the GET,
  which may duplicate application work or patches.
- Never enable this automatically for mutating requests.

Datastar closes GET SSE connections in hidden tabs by default unless `openWhenHidden` is
set, and HTMX 4 documents background SSE pausing with Last-Event-ID resumption.
HyperDjango's explicit checkpoint design makes the optimization possible, but it should
remain opt-in because resume correctness is application-owned.

Sources:

- [Datastar action options](https://data-star.dev/reference/actions)
- [HTMX 4.0.0 release](https://github.com/bigskysoftware/htmx/releases/tag/v4.0.0)

### 5. Lazy fragment loading — priority 3/5

Add a narrow declarative primitive that calls a read-only action when a
server-rendered fragment enters the viewport:

```html
<section id="activity"
         hyper-action="load_activity"
         hyper-trigger="visible"
         hyper-action-data='{"project_id": 42}'></section>
```

The response should still pass through the normal target, focus, lifecycle,
strict-target, and inspector pipeline. Reusing the current page's GET action
endpoint follows HyperDjango's action convention and avoids a fragment-only URL.

This is useful for expensive dashboards and below-the-fold panels. It is lower priority
than correct head and DOM lifecycle handling because it introduces cache, cancellation,
and accessibility questions.

Source:

- [Turbo Frames lazy loading](https://turbo.hotwired.dev/handbook/frames#lazy-loading-frames)

### 6. Non-destructive signal initialization — priority 3/5

Datastar's signal patches support an `onlyIfMissing` option. The equivalent would be a
small extension to HyperDjango's Alpine-specific `Signals` action:

```python
Signals({"filters": defaults}, only_if_missing=True)
```

This lets a stream initialize state without overwriting edits already made in the browser.
It should not expand into a second reactive expression language: HyperDjango already has
a clean boundary where Alpine owns local reactivity and the server sends explicit patches.

Source:

- [Datastar SSE events](https://data-star.dev/reference/sse_events)

### 7. Optional prefetch extension — priority 2/5

A small opt-in extension could prefetch same-origin GET navigation responses on intent
(pointer hover, focus, or touch start) and consume them only while validators and request
context still match. It must honor authentication, `Cache-Control`, `Vary`, CSP, and a
strict memory bound. Do not prefetch actions or mutating forms.

This can improve perceived navigation latency, but native browser caching already handles
many cases and incorrect reuse is worse than a network round trip. It should follow head
reconciliation and response selection rather than precede them.

Sources:

- [HTMX extension architecture](https://htmx.org/docs/#extensions)
- [Turbo page caching](https://turbo.hotwired.dev/handbook/building#understanding-caching)

## Features not worth copying into core

### DOM snapshot history

HTMX 2 and Turbo cache DOM snapshots for restoration. HyperDjango deliberately treats the
URL and a normal GET as the source of truth. Keep that design. It avoids persisting
sensitive or stale DOM and matches HTMX 4's move toward full-page history requests.

Sources:

- [HTMX 2 history](https://htmx.org/docs/#history)
- [HTMX 4 documentation](https://four.htmx.org/docs)

### A second reactive expression engine

Datastar's signals, computed expressions, effects, and bindings are central to Datastar,
but HyperDjango already delegates local reactivity to Alpine. Reimplementing that layer
would enlarge the runtime and CSP/XSS surface while creating two competing state models.
Datastar's own security documentation notes that client state is visible and mutable and
that its expression evaluation needs an explicit CSP mode.

Source:

- [Datastar security](https://data-star.dev/reference/security)

### WebSockets or pub/sub in the core package

HyperDjango actions are request/response streams with explicit reconnect semantics.
WebSockets require connection ownership, backplanes, authorization refresh, delivery
semantics, and deployment integration that belong in an optional Django Channels adapter.
Do not hide those costs behind the existing action API.

Sources:

- [HTMX WebSocket extension](https://htmx.org/extensions/ws/)
- [HTMX SSE extension](https://htmx.org/extensions/sse/)

### Generic out-of-band HTML magic

HyperDjango already represents multiple target updates as an ordered list of typed
`HTML(...)` or `Delete(...)` items. That is easier to validate, inspect, and test than
embedding target instructions in arbitrary response markup. Keep the typed protocol.

### Automatic retries for mutating actions

HyperDjango's GET-default/POST-opt-in retry policy and explicit idempotency guidance are
stronger than a generic retry switch. Datastar's retry options are useful evidence for
bounded backoff and lifecycle events, both of which HyperDjango already implements. Do not
infer safety from the HTTP method or hide mutation retries in server decorators.

Source:

- [Datastar action retry options](https://data-star.dev/reference/actions)

### HTTP `QUERY`

Datastar 1.0.4 added a `QUERY` action, but intermediary and Django ecosystem support is not
yet broad enough to justify expanding HyperDjango's public method contract. GET with
explicit parameters remains more interoperable for read actions.

Source:

- [Datastar 1.0.4 release](https://github.com/starfederation/datastar/releases/tag/v1.0.4)

## Suggested implementation order

1. Add a browser reproducer for navigation between two routes with disjoint head CSS and
   JS, then implement head reconciliation.
2. Specify `hyper-preserve` and an explicit morph/replacement strategy together so
   element identity has one public contract.
3. Add `hyper-select` using the existing strict-target and inspector diagnostics.
4. Add hidden-tab suspension only for explicitly resumable GET workflows.
5. Pilot lazy loading and prefetch as optional HTML/runtime extensions.
6. Add `only_if_missing` to signal patches if real applications demonstrate clobbered
   initialization state.

## Repository evidence reviewed

- `hyperdjango/actions.py`
- `hyperdjango/integrations/alpine/actions.py`
- `hyperdjango/runtime/dispatcher.py`
- `hyperdjango/runtime/responses.py`
- `hyperdjango/sse.py`
- `hyperdjango/page.py`
- `hyperdjango/assets/resolver.py`
- `hyperdjango/static/hyperdjango/hyper.js`
- `docs/actions.md`
- `docs/history.md`
- `docs/reference/client-runtime.md`
- `docs/assets-and-vite.md`
- `docs/dev-toolbar.md`
- `CHANGELOG.md`
