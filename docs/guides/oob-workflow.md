# OOB Workflow Guide

Out-of-band (OOB) updates let one response update multiple DOM regions.

Use this when one action changes:

- the main content area
- secondary widgets (stats, flash, badges, counters)

## Typical Pattern

Return primary swap + OOB updates together:

```python
return self.action_response(
    html=row_html,
    target="#todo-list",
    swap="append",
    oob={
        "#todo-stats": {"swap": "inner", "html": stats_html},
        "#flash": {"swap": "inner", "html": flash_html},
    },
)
```

Result:

- `#todo-list` receives append swap
- `#todo-stats` and `#flash` update in the same response cycle

## OOB Payload Shapes

### Selector-keyed object

```json
{
  "#stats": { "swap": "inner", "html": "<div>3</div>" }
}
```

### Ordered array

```json
[
  { "target": "#stats", "swap": "inner", "html": "<div>3</div>", "order": 1 },
  { "target": "#flash", "swap": "inner", "html": "<p>Saved</p>", "order": 2 }
]
```

## Choosing OOB vs Signals

- use **OOB** for DOM fragments in other regions
- use **signals** for data/state patches consumed by Alpine
- use both when needed

## Debugging Tips

- enable strict targets (`hyper-strict-targets="true"`) in QA
- keep OOB selectors stable and unique
- prefer rendering server partials for repeated fragments
