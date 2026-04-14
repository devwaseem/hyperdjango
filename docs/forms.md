# Forms

`$action(..., data, { form })` enhances standard Django forms without replacing Django validation or rendering.

It preserves Django Form ergonomics (server validation, error rendering, CSRF defaults) while adding partial updates, request sync, and loading UX.

## Minimal Example

```html
<form id="profile-form"
  x-data="{}"
  method="post"
  action="/profile"
  x-on:submit.prevent="$action('save_profile', {}, {
    form: $el,
    sync: 'block'
  })">
  {% csrf_token %}
  {{ form.email }} {{ form.email.errors }}
  {{ form.name }} {{ form.name.errors }}
  <button type="submit">Save</button>
</form>
```

## How It Works

- `form: $el` or `form: '#form-id'` in the third argument tells Hyper to build the request from the form element
- form `method` and `action` are used automatically
- `GET` forms send field values as action kwargs
- non-`GET` forms send `FormData`, so uploads continue to work
- action name stays explicit in `$action('save_profile', {}, ...)`

Use `$action(...)` options for request behavior such as:

- `sync`
- `key`
- `method`
- `onUploadProgress`

Swap target, swap mode, transition, focus, history, and related UI behavior should come from the server response.

## GET vs Non-GET

This split keeps GET requests URL-friendly and cacheable while preserving normal `FormData`/CSRF behavior for writes.

- `GET`: sends kwargs through `X-Hyper-Data`
- non-`GET`: sends `FormData` with CSRF and `_action`

## Server Pattern (Django `Form`)

```python
from django import forms
from hyperdjango.actions import action
from hyperdjango.page import HyperView


class ProfileForm(forms.Form):
    email = forms.EmailField()
    name = forms.CharField(max_length=80)


class PageView(HyperView):
    @action
    def save_profile(self, request):
        form = ProfileForm(request.POST)
        if not form.is_valid():
            return self.action_response(
                target="#profile-form",
                swap="outer",
                content=self.render_block(
                    request=request,
                    block_name="save_profile",
                    context_updates={"form": form},
                ),
                focus="first-invalid",
                status=422,
            )

        return self.action_response(
            target="#profile-result",
            content=self.render_block(
                request=request,
                block_name="profile_success",
                context_updates={"data": form.cleaned_data},
            ),
            toast={"type": "success", "message": "Profile saved"},
        )
```
