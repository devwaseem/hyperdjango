# Alpine Integration

HyperDjango works without Alpine, but Alpine is the integration layer it supports most directly.

Use Alpine when you want:

- `$action(...)`
- concise local state
- signal patching into `x-data`
- signal patching into `$store.hyper`

## `$action(...)`

When Alpine is present, HyperDjango installs the `$action(...)` magic automatically.

```html
<div x-data="{ q: '' }">
  <input x-model="q" />
  <button @click="$action('search', { q }, { key: 'search' })">Search</button>
</div>
```

## Local Signals

An unprefixed signal name patches the nearest Alpine `x-data` scope.

```python
from __future__ import annotations

from hyperdjango.actions import action
from hyperdjango.integrations.alpine.actions import Signal
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def counter(self, request, count: int = 0):
        return [Signal(name="count", value=int(count) + 1)]
```

```html
<section x-data="{ count: 0 }">
  <button @click="$action('counter', { count })">Increment</button>
  <strong x-text="count"></strong>
</section>
```

## Global Signals

A signal name starting with `$` patches `Alpine.store("hyper")`.

```python
from __future__ import annotations

from hyperdjango.actions import action
from hyperdjango.integrations.alpine.actions import Signal
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def reset_global(self, request):
        return [Signal(name="$count", value=0)]
```

```html
<section x-data="{}" x-init="$store.hyper.count = 5">
  <button @click="$action('reset_global')">Reset global</button>
  <strong x-text="$store.hyper.count"></strong>
</section>
```

## Local and Global Together

```python
from __future__ import annotations

from hyperdjango.actions import action
from hyperdjango.integrations.alpine.actions import Signals
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def increment_both(self, request, current: int = 0):
        local_count = int(current) + 1
        global_count = 42
        return [Signals(values={"count": local_count, "$count": global_count})]
```

```html
<section x-data="{ count: 0 }" x-init="$store.hyper.count = 0">
  <button @click="$action('increment_both', { current: count })">Increment</button>
  <p>Local: <strong x-text="count"></strong></p>
  <p>Global: <strong x-text="$store.hyper.count"></strong></p>
</section>
```
