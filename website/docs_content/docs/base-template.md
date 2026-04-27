# Base Template

HyperDjango ships a base template at `hyperdjango/base.html`.

Use it when you want the fastest path to a working app with the runtime scripts, asset tags, and CSRF hooks already in place.

## What It Provides

The shipped template includes:

- `{% hyper_preloads %}`
- `{% hyper_stylesheets %}`
- `{% hyper_head_scripts %}`
- `{% hyper_body_scripts %}`
- the core runtime script: `hyper.js`
- the Alpine bridge script: `hyper-alpine.js`
- a hidden CSRF token mount
- a `head` block and a `body` block you can extend normally

Current template:

```django
{% load static hyper_tags %}
<!DOCTYPE html>
<html lang="en">
    <head>
        {% block head %}
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>{{ title|default:"HyperDjango" }}</title>
        {% endblock head %}
        {% hyper_preloads %}
        {% hyper_stylesheets %}
        {% hyper_head_scripts %}
    </head>
    <body>
        <div id="hyper-csrf-token" hidden>{% csrf_token %}</div>
        {% block body %}
        {% endblock body %}
        <script src="{% static 'hyperdjango/hyper.js' %}"></script>
        <script src="{% static 'hyperdjango/hyper-alpine.js' %}"></script>
        {% hyper_body_scripts %}
    </body>
</html>
```

## Extending It

The normal pattern is to extend `hyperdjango/base.html` from your layout template.

```django
{% extends "hyperdjango/base.html" %}

{% block body %}
  <nav>...</nav>
  <main>{% block page %}{% endblock page %}</main>
{% endblock body %}
```

This works well for `hyper/layouts/...` packages.

## When to Use It

Use the shipped base template when you want:

- automatic page asset tags
- the runtime scripts already included
- CSRF wiring already present
- the default HyperDjango browser behavior without extra setup

For most projects, this should be the default starting point.

## Replacing It With Your Own Base Template

You can use your own base template instead.

If you do, keep these pieces:

### Load the template tags

```django
{% load static hyper_tags %}
```

### Render asset tags

In the head:

```django
{% hyper_preloads %}
{% hyper_stylesheets %}
{% hyper_head_scripts %}
```

Before the end of the body:

```django
{% hyper_body_scripts %}
```

### Include the runtime scripts

```django
<script src="{% static 'hyperdjango/hyper.js' %}"></script>
<script src="{% static 'hyperdjango/hyper-alpine.js' %}"></script>
```

If you do not want Alpine integration, you can omit `hyper-alpine.js`.

### Provide a CSRF source

The default template uses:

```django
<div id="hyper-csrf-token" hidden>{% csrf_token %}</div>
```

Keep that or provide an equivalent CSRF source the runtime can read.

## Minimal Custom Base

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
  <body>
    <div id="hyper-csrf-token" hidden>{% csrf_token %}</div>
    {% block body %}{% endblock body %}
    <script src="{% static 'hyperdjango/hyper.js' %}"></script>
    <script src="{% static 'hyperdjango/hyper-alpine.js' %}"></script>
    {% hyper_body_scripts %}
  </body>
</html>
```

## Related Pages

- Assets and Vite: where the asset tags get their data
- Declarative HTML APIs: loading states, form-disable behavior, and view-transition naming
- Layouts: how your app-level templates usually extend the base template
