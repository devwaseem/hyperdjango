# Actions

Actions are the server-side interaction API of HyperDjango.

Use page handlers like `get()` and `post()` for full-page rendering.

Use `@action` for interaction-level updates.

## What an Action Is

An action is a method marked with `@action`.

```python
from __future__ import annotations

from hyperdjango.actions import HTML, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def save(self, request):
        return [HTML(content="<div id='flash'>Saved</div>", target="#flash")]
```

Actions let the server tell the browser to:

- patch HTML
- remove elements
- dispatch browser events
- show toasts
- redirect
- update history
- load JavaScript
- patch Alpine signals when Alpine integration is in use

## Recommended Return Shapes

The clearest action return styles are:

`list of action items`

Use a list when the whole response is known immediately.

```python
from __future__ import annotations

from hyperdjango.actions import HTML, Toast, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def create(self, request):
        return [
            HTML(content="<li>New item</li>", target="#todo-list", swap="append"),
            Toast(payload={"type": "success", "message": "Created"}),
        ]
```

`generator of action items`

Use a generator when items should be streamed over time.

```python
from __future__ import annotations

from time import sleep

from hyperdjango.actions import HTML, Redirect, Toast, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def run_job(self, request):
        yield HTML(content="<p id='job-status'>Starting...</p>", target="#job-status")
        sleep(1)
        yield HTML(content="<p id='job-status'>Working...</p>", target="#job-status")
        sleep(1)
        yield Toast(payload={"type": "success", "message": "Done"})
        yield Redirect(url="/done/")
```

Treat `Redirect(...)` as the last action item. Once the runtime sends a redirect, later items are not delivered.

## Other Supported Return Shapes

The current runtime also accepts a few other return forms.

`single action item`

```python
from __future__ import annotations

from hyperdjango.actions import HTML, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def save(self, request):
        return HTML(content="<div id='flash'>Saved</div>", target="#flash")
```

`Actions(...)`

```python
from __future__ import annotations

from hyperdjango.actions import Actions, HTML, Toast, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def create(self, request):
        return Actions(
            HTML(content="<li>New item</li>", target="#todo-list", swap="append"),
            Toast(payload={"type": "success", "message": "Created"}),
        )
```

`str`

```python
from __future__ import annotations

from hyperdjango.actions import action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def simple(self, request):
        return "<div id='flash'>Saved</div>"
```

`dict`

A `dict` is treated as context for block rendering from the current page template.

```python
from __future__ import annotations

from hyperdjango.actions import action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def stats(self, request):
        return {"count": 12, "completed": 4}
```

```django
{% block stats %}
  <div><strong>{{ count }}</strong> total, <strong>{{ completed }}</strong> completed</div>
{% endblock stats %}
```

`HttpResponse`

```python
from __future__ import annotations

from django.http import HttpResponse

from hyperdjango.actions import action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def download(self, request):
        return HttpResponse("ok", content_type="text/plain")
```

## Typed Action Items

### `HTML`

Use `HTML(...)` to patch HTML into the page.

```python
from __future__ import annotations

from hyperdjango.actions import HTML, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def save(self, request):
        return [
            HTML(
                content="<div id='flash'>Saved</div>",
                target="#flash",
                swap="outer",
                transition=True,
                focus="preserve",
            )
        ]
```

### `Delete`

Use `Delete(...)` to remove a target element.

```python
from __future__ import annotations

from hyperdjango.actions import Delete, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def remove_row(self, request, id: int):
        return [Delete(target=f"#row-{id}")]
```

### `Event`

Use `Event(...)` to dispatch a browser `CustomEvent`.

```python
from __future__ import annotations

from hyperdjango.actions import Event, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def save_profile(self, request):
        return [Event(name="profile:saved", payload={"message": "Saved"}, target="#panel")]
```

### `Toast`

Use `Toast(...)` to emit a toast payload.

```python
from __future__ import annotations

from hyperdjango.actions import Toast, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def save(self, request):
        return [Toast(payload={"type": "success", "message": "Saved"})]
```

### `Redirect`

Use `Redirect(...)` when the interaction should leave the current page.

```python
from __future__ import annotations

from hyperdjango.actions import Redirect, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def finish(self, request):
        return [Redirect(url="/dashboard/")]
```

### `History`

Use `History(...)` when the URL should change without leaving the current page.

```python
from __future__ import annotations

from hyperdjango.actions import History, HTML, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def filter(self, request, q: str = ""):
        return [
            History(replace_url=f"/search/?q={q}"),
            HTML(content=f"<div id='results'>Results for {q}</div>", target="#results"),
        ]
```

### `LoadJS`

Use `LoadJS(...)` when an action-loaded fragment needs its own JS module.

```python
from __future__ import annotations

from hyperdjango.actions import HTML, LoadJS, action
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def open_modal(self, request):
        partial = self.render_template(
            "partials/confirm_modal",
            request=request,
            context_updates={"title": "Confirm", "message": "Continue?"},
        )
        items = [HTML(content=partial.html, target="#modal-root", swap="inner")]
        if partial.js:
            items.append(LoadJS(src=partial.js))
        return items
```

### `Signal` and `Signals`

Signals are Alpine-oriented state patches.

```python
from __future__ import annotations

from hyperdjango.actions import action
from hyperdjango.integrations.alpine.actions import Signal, Signals
from hyperdjango.page import HyperView


class PageView(HyperView):
    @action
    def counter(self, request, count: int = 0):
        return [Signal(name="count", value=int(count) + 1)]

    @action
    def increment_both(self, request, current: int = 0):
        local_count = int(current) + 1
        global_count = 42
        return [Signals(values={"count": local_count, "$count": global_count})]
```

- `count` patches the nearest Alpine `x-data`
- `$count` patches `Alpine.store("hyper")`
