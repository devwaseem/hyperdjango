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

Example:

```javascript
$action("save", data, { method: "POST", target: "#panel", swap: "outer" })
```

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

Enable per call:

```javascript
$action("save", data, { method: "POST", target: "#panel", strictTargets: true })
```

Enable globally:

```html
<body hyper-strict-targets="true">
```

## OOB Updates

Out-of-band updates let one response update elements outside the primary target.

Object format:

```json
{
  "#stats": { "swap": "inner", "html": "<div>3</div>" }
}
```

Array format:

```json
[
  { "target": "#stats", "swap": "inner", "html": "<div>3</div>", "order": 1 }
]
```
