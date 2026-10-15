# Migration Guide

This guide covers intentional breaking changes that require application updates when upgrading HyperDjango.

## Migrating to 0.45.0

### Rename browser event listeners

HyperDjango browser events now use colon-separated namespaces consistently. The runtime no longer emits the previous camelCase names, so update every listener during the upgrade.

| Previous event | Replacement |
| --- | --- |
| `hyper:beforeRequest` | `hyper:request:before` |
| `hyper:afterRequest` | `hyper:request:after` |
| `hyper:requestBlocked` | `hyper:request:blocked` |
| `hyper:requestReplaced` | `hyper:request:replaced` |
| `hyper:requestAborted` | `hyper:request:aborted` |
| `hyper:requestSuccess` | `hyper:request:success` |
| `hyper:requestError` | `hyper:request:error` |
| `hyper:requestException` | `hyper:request:exception` |
| `hyper:requestRetry` | `hyper:request:retry` |
| `hyper:requestRetriesFailed` | `hyper:request:retries:failed` |
| `hyper:requestPaused` | `hyper:request:paused` |
| `hyper:requestResumed` | `hyper:request:resumed` |
| `hyper:uploadProgress` | `hyper:upload:progress` |
| `hyper:streamEvent` | `hyper:stream:event` |
| `hyper:actionSwitch` | `hyper:action:switch` |
| `hyper:form:beforeSubmit` | `hyper:form:submit:before` |

For JavaScript listeners, replace the event name directly:

```js
window.addEventListener("hyper:request:after", (event) => {
  console.log(event.detail.status);
});
```

For Alpine listeners, use the colon-separated event name without the old `.camel` conversion:

```html
<div @hyper:action:switch.window="handleSwitch($event.detail)"></div>
```

Update application code, custom integrations, browser tests, and monitoring that subscribe to these events. The event payloads and firing order are unchanged.

### Verify the migration

Search the application for legacy names before upgrading. No `hyper:*` event name should contain an uppercase letter, and Alpine listeners should not use kebab-case names with `.camel` to reconstruct a HyperDjango event.

Then exercise actions, uploads, streaming retries, enhanced navigation, and any debugger integration that consumes request lifecycle events.
