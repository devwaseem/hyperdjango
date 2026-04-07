# Request Lifecycle Guide

This guide shows how a Hyper request flows from trigger to DOM update.

## 1) Trigger

A request can start from:

- `$get(...)` / `$post(...)`
- `hyper-form`
- `hyper-nav` links/forms

For action requests, the runtime sends:

- `X-Hyper-Action`
- optional `X-Hyper-Signals`
- optional `X-Hyper-Target`

## 2) Sync Coordination

Before fetch starts, sync policy is applied:

- `replace`: abort previous in-flight request in same key
- `block`: skip new request if one is active
- `none`: no coordination

Use explicit `key` for stable request lanes:

```javascript
$get("search", { q }, { sync: "replace", key: "live-search" })
```

## 3) Loading State

While request is active, runtime updates:

- `<html hyper-loading>`
- `aria-busy` on `<html>` and `<body>`
- scoped loading indicators (`hyper-loading*`)
- scoped disable controls (`hyper-loading-disable*`)

## 4) Response Handling

### HTML response

- swapped into `target` (if provided)

### JSON action response

- applies `signals`
- emits `hyper:toast`
- performs target swap based on `target` and `swap`
- applies `oob` operations
- updates history if `push_url` / `replace_url` is set

## 5) Lifecycle Hooks

Primary events in order:

1. `hyper:beforeRequest`
2. one of `hyper:requestSuccess` or `hyper:requestError`
3. `hyper:afterRequest`

DOM mutation hooks:

- `hyper:swap:start`
- `hyper:swap:end`
- `hyper:settle:end`

Transition hooks:

- `hyper:transition:start`
- `hyper:transition:end`

See full event contract in `docs/events.md`.
