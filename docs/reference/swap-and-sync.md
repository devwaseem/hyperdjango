# Swap and Sync Reference

## Swap Modes

Hyper swap modes control how response HTML is applied to a target.

Allowed values:

- `inner`: replace inner content
- `outer`: replace target element
- `before`: insert before target
- `after`: insert after target
- `prepend`: insert at target start
- `append`: insert at target end
- `delete`: remove target element
- `none`: do not mutate target

Server responses control swap targets and swap modes for actions. Use typed items like `HTML(...)` and `Delete(...)` on the server.

## Sync Modes

Sync controls concurrent requests in the same sync group.

Allowed values:

- `replace`: abort old request and run new one
- `block`: ignore new request while old one runs
- `none`: allow overlap

Example:

```javascript
$action("search", { q }, { sync: "replace", key: "live-search" })
```

## Sync Keys

`key` groups requests into a coordination lane.

- same `key` => sync applies between those requests
- different keys => independent lanes

## Strict Targets

Strict mode throws when a target selector is missing.

Enable globally:

```html
<body hyper-strict-targets="true">
```

## Multiple Patches

Server responses can emit multiple `HTML(...)` and `Delete(...)` items in one action stream.

Example:

```python
return Actions(
    HTML(content=main_html, target="#panel"),
    HTML(content=stats_html, target="#stats"),
    Delete(target="#row-1"),
)
```
