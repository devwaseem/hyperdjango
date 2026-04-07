# Forms

`hyper-form` enhances standard Django forms without replacing Django validation or rendering.

It preserves Django Form ergonomics (server validation, error rendering, CSRF defaults) while adding partial updates, request sync, and loading UX.

## Minimal Example

```html
<form
  method="post"
  action="/profile"
  hyper-form
  hyper-action="save_profile"
  hyper-target="#profile-form"
  hyper-form-disable
>
  {% csrf_token %}
  <input type="hidden" name="_action" value="save_profile" />
  {{ form.email }} {{ form.email.errors }}
  {{ form.name }} {{ form.name.errors }}
  <button type="submit">Save</button>
</form>
```

## Form Attributes

These attributes exist so form behavior is explicit in markup and can be tuned per form (for example block submit sync for write actions).

- `hyper-form`: enable enhancement
- `hyper-action`: action name (fallback: hidden `_action`)
- `hyper-target`: swap target selector
- `hyper-swap`: swap mode
- `hyper-sync`: sync mode (`block` default for hyper-form)
- `hyper-key`: sync key (fallback: action name)
- `hyper-transition`: enable View Transition for form updates
- `hyper-focus`: post-swap focus policy
- `hyper-form-disable`: auto-apply disable scope to form controls
- `hyper-strict-targets`: local strict mode
- `hyper-swap-delay`, `hyper-settle-delay`

## GET vs Non-GET

This split keeps GET requests URL-friendly and cacheable while preserving normal `FormData`/CSRF behavior for writes.

- `GET`: sends kwargs through `X-Hyper-Signals`
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
                html=self.render_block(
                    request=request,
                    block_name="save_profile",
                    context_updates={"form": form},
                ),
                focus="first-invalid",
                status=422,
            )

        return self.action_response(
            target="#profile-result",
            swap="inner",
            html=self.render_block(
                request=request,
                block_name="profile_success",
                context_updates={"data": form.cleaned_data},
            ),
            toast={"type": "success", "message": "Profile saved"},
        )
```
