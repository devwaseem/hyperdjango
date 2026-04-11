# Form Attributes Reference

Preferred form style uses `$action(name, data, { form })` from Alpine or JS. These attributes remain available when you want declarative compatibility without JS expressions.

## `hyper-action`

Sets action name for form submission.

- fallback: hidden input `_action`

## `hyper-sync`

Request sync behavior.

Allowed values:

- `replace`: replace in-flight request in same key
- `block`: ignore new request while one is active
- `none`: no sync coordination

Default is `block`.

## `hyper-key`

Sync group key.

- fallback: action name

## `hyper-form-disable`

Applies disable scope to form controls while request is active.

## Example

```html
<form
  method="post"
  action="/profile"
  hyper-action="save_profile"
  hyper-sync="block"
  hyper-key="profile-save"
  hyper-form-disable
>
  {% csrf_token %}
  <input type="hidden" name="_action" value="save_profile" />
  ...
</form>
```

Preferred equivalent:

```html
<form x-data="{}"
  method="post"
  action="/profile"
  x-on:submit.prevent="$action('save_profile', {}, {
    form: $el,
    sync: 'block',
    key: 'profile-save'
  })">
  {% csrf_token %}
  ...
</form>
```
