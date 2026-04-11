# Custom Base Template

You can use your own base template instead of `hyperdjango/base.html`.

A custom base works as long as it includes the required HyperDjango hooks.

## Required Hooks

1. Load template tags:

```django
{% load static hyper_tags %}
```

2. Render asset tags:

- in `<head>`: `{% hyper_preloads %}`, `{% hyper_stylesheets %}`, `{% hyper_head_scripts %}`
- before `</body>`: `{% hyper_body_scripts %}`

3. Include runtime script:

```django
<script src="{% static 'hyperdjango/hyper.js' %}"></script>
```

4. Provide CSRF source for runtime requests (one of):

- hidden csrf mount: `<div id="hyper-csrf-token" hidden>{% csrf_token %}</div>`
- or `<meta name="csrf-token" content="...">`

5. (Recommended) Set popstate target:

```html
<body hyper-pop-target="body">
```

## Minimal Example

```django
{% load static hyper_tags %}
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{{ title|default:"My App" }}</title>
    {% hyper_preloads %}
    {% hyper_stylesheets %}
    {% hyper_head_scripts %}
  </head>
<body hyper-pop-target="body">
    <div id="hyper-csrf-token" hidden>{% csrf_token %}</div>
    {% block body %}{% endblock body %}
    <script src="{% static 'hyperdjango/hyper.js' %}"></script>
    {% hyper_body_scripts %}
  </body>
</html>
```

## Notes

- You do not need a query-string version suffix on `hyper.js`.
- You can add your own CSS/animations for `hyper-swapping` and `hyper-settling` classes.
- If navigation enhancement is used, default target is `body` unless overridden by `hyper-target`.
