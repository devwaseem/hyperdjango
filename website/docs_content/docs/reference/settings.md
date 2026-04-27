# Settings

## `HYPER_FRONTEND_DIR`

Type:

- `Path | str`

Purpose:

- tells HyperDjango where your `hyper/` directory lives

Expected contents usually include:

- `routes/`
- `layouts/`
- `templates/`
- shared frontend files

Example:

```python
HYPER_FRONTEND_DIR = BASE_DIR / "hyper"
```

## `HYPER_VITE_OUTPUT_DIR`

Type:

- `Path | str`

Purpose:

- tells HyperDjango where Vite writes built assets

Example:

```python
HYPER_VITE_OUTPUT_DIR = BASE_DIR / "dist"
```

## `HYPER_VITE_DEV_SERVER_URL`

Type:

- `str`

Purpose:

- tells HyperDjango which Vite dev server URL to inject during development

Example:

```python
HYPER_VITE_DEV_SERVER_URL = "http://localhost:5173/"
```

## `HYPER_DEV`

Type:

- `bool`

Purpose:

- switches asset loading between development mode and manifest-based production mode

Typical usage:

```python
HYPER_DEV = DEBUG
```

Behavior:

- `True`: use Vite dev server URLs and inject `@vite/client`
- `False`: resolve assets from the built Vite manifest in `HYPER_VITE_OUTPUT_DIR`
