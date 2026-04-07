# Form Attributes Reference

These attributes apply to forms using `hyper-form`.

## `hyper-form`

Enables Hyper form submission flow.

- keeps Django form validation/rendering server-side
- supports partial swaps, sync, transitions, loading controls

## `hyper-action`

Sets action name for form submission.

- fallback: hidden input `_action`

## `hyper-target`

Target selector for form response swap.

## `hyper-swap`

Swap mode for form response target.

Allowed values:

- `inner`, `outer`, `before`, `after`, `prepend`, `append`, `delete`, `none`

## `hyper-sync`

Request sync behavior.

Allowed values:

- `replace`: replace in-flight request in same key
- `block`: ignore new request while one is active
- `none`: no sync coordination

For `hyper-form`, default is `block`.

## `hyper-key`

Sync group key.

- fallback: action name

## `hyper-form-disable`

Applies disable scope to form controls while request is active.

## `hyper-focus`

Post-swap focus policy.

Allowed values:

- `preserve`
- `first-invalid`
- CSS selector

## `hyper-transition`

Enables View Transitions for this form interaction.

## Timing Attributes

- `hyper-swap-delay`: delay before swap (ms)
- `hyper-settle-delay`: delay for settle phase (ms)

## `hyper-strict-targets`

Enables strict target enforcement for this form request.

## Example

```html
<form
  method="post"
  action="/profile"
  hyper-form
  hyper-action="save_profile"
  hyper-target="#profile-panel"
  hyper-swap="outer"
  hyper-sync="block"
  hyper-key="profile-save"
  hyper-focus="first-invalid"
  hyper-form-disable
>
  {% csrf_token %}
  <input type="hidden" name="_action" value="save_profile" />
  ...
</form>
```
