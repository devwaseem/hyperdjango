# Multi-Patch Workflow Guide

Multiple targeted HTML patches let one response update multiple DOM regions.

Use this when one action changes:

- the main content area
- secondary widgets (stats, flash, badges, counters)

## Typical Pattern

Return primary swap + additional targeted patches together:

```python
return Actions(
    HTML(content=row_html, target="#todo-list", swap="append"),
    HTML(content=stats_html, target="#todo-stats"),
    HTML(content=flash_html, target="#flash"),
)
```

Result:

- `#todo-list` receives append swap
- `#todo-stats` and `#flash` update in the same response cycle

## Ordering

Patch order is determined directly by the order of items in the returned list/generator.

## Choosing HTML Patches vs Signals

- use targeted **HTML(...)** patches for DOM fragments in other regions
- use **signals** for data/state patches consumed by Alpine
- use both when needed

## Debugging Tips

- enable strict targets (`hyper-strict-targets="true"`) in QA
- keep patch target selectors stable and unique
- prefer rendering server partials for repeated fragments
