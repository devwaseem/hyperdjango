# Cookbook

Copy-paste recipes for common HyperDjango interaction patterns.

The cookbook shows practical composition of features in real flows, not just isolated API references.

## 1) Button -> server action -> local Alpine state sync

```html
<section x-data="{ count: 0 }">
  <button x-on:click="$action('increment', { current: count })">
    Increment
  </button>
  <strong x-text="count"></strong>
</section>
```

```python
@action
def increment(self, request, current=0, **params):
    return self.action_response(signals={"count": int(current) + 1})
```

### Local + global patch (`count` + `$count`)

```python
@action
def increment(self, request, current=0, **params):
    value = int(current) + 1
    return self.action_response(
        signals={
            "count": value,
            "$count": value,
        }
    )
```

```html
<section x-data="{ count: 0 }">
  <button x-on:click="$action('increment', { current: count })">Increment</button>
  <p>Local: <span x-text="count"></span></p>
  <p>Global: <span x-text="$hyper.count"></span></p>
</section>
```

## 2) Partial swap with server-selected target

```python
@action
def show_editor(self, request, **params):
    return self.action_response(
        html=self.render(request=request, relative_template_name="partials/editor_form.html"),
        target="#editor",
        swap="inner",
    )
```

Client call can omit `target` and use server contract.

## 3) Multiple targeted HTML patches to keep side panels in sync

```python
@action
def add_todo(self, request, title="", **params):
    return Actions(
        HTML(content="<li>...</li>", target="#todo-list", swap="append"),
        HTML(content="<div>Updated stats</div>", target="#todo-stats"),
        HTML(content="<p>Added</p>", target="#flash"),
    )
```

## 4) Ordered multi-patch updates

```python
return Actions(
    HTML(content="A", target="#one"),
    HTML(content="<div id='two'>B</div>", target="#two", swap="outer"),
)
```

## 5) Delete row without sending HTML

```python
from hyperdjango.actions import Delete


return [Delete(target=f"#todo-{id}")]
```

## 6) Typeahead with request replacement

```text
<input
  x-model="q"
  x-on:input.debounce.250ms="$action('search', { q }, { sync: 'replace', key: 'live-search' })"
/>
```

New requests abort in-flight ones in the same key.

## 7) Prevent double submits with sync block

```html
<form id="profile-form"
  x-data="{}"
  x-on:submit.prevent="$action('save_profile', {}, { form: $el, sync: 'block', key: 'profile-save' })">
  ...
</form>
```

New submits while pending are ignored (blocked).

## 8) Loading spinner + disable controls

```html
<div hyper-loading="live-search" hyper-loading-delay="150">Searching...</div>
<button hyper-loading-disable="live-search">Search</button>
```

## 9) Form validation with focus to first invalid field

```python
if not form.is_valid():
    return self.action_response(
        html=self.render(request=request, relative_template_name="partials/form.html", context_updates={"form": form}),
        target="#profile-panel",
        focus="first-invalid",
        status=422,
    )
```

## 10) Push or replace URL from actions

```python
return self.action_response(
    html="...",
    target="#results",
    replace_url=f"/search?q={query}",
)
```

Use `push_url` when you want a new history entry instead.

## 11) Progressive nav opt-in (links/forms)

```html
<a href="/todos" hyper-nav hyper-target="body">Todos</a>
<form method="get" action="/search" hyper-nav hyper-target="body">
  ...
</form>
```

No `hyper-nav` means normal browser navigation.

## 12) Strict target mode in QA

```html
<body hyper-strict-targets="true">
```

Missing target selectors throw errors early and surface integration drift.

## 13) Use `HyperPageTemplate` in a custom Django view

```python
from hyperdjango.page import HyperPageTemplate


class ProfileCardTemplate(HyperPageTemplate):
    pass
```

```python
from hyperdjango.shortcuts import render_template_page


def profile_card(request):
    return render_template_page(
        request,
        ProfileCardTemplate,
        context={"title": "Account", "description": "From custom view"},
    )
```
