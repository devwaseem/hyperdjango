# Vite Production Build

This guide covers building frontend assets for production and wiring them with Django static files.

## How HyperDjango Resolves Assets

In production mode (`HYPER_DEV = False`), HyperDjango resolves asset tags from Vite's `manifest.json` in `HYPER_VITE_OUTPUT_DIR`.

That means your deploy must include:

- built assets
- `manifest.json`
- Django static collection including that output directory

## 1) Build Frontend Assets

From project root (or wherever `package.json` lives):

```bash
npm install
npm run build
```

Your `vite.config.js` should output to your configured build directory (commonly `dist/`).

## 2) Django Settings for Production

```python
HYPER_DEV = False
HYPER_VITE_OUTPUT_DIR = BASE_DIR / "dist"
STATICFILES_DIRS = [HYPER_VITE_OUTPUT_DIR]
```

`HYPER_VITE_DEV_SERVER_URL` is ignored for manifest-based production asset resolution.

## 3) Collect Static Files

```bash
python manage.py collectstatic --noinput
```

This includes HyperDjango runtime static files and Vite output.

## 4) Deploy

Deploy code + collected static output as you normally do for Django.

## Environment Variable Pattern

If your `vite.config.js` reads `VITE_APP_OUTPUT_DIR`, set it explicitly in CI/CD:

```bash
VITE_APP_OUTPUT_DIR=./dist npm run build
```

Use the same path in Django `HYPER_VITE_OUTPUT_DIR`.

## CI Example

```bash
npm ci
npm run build
python manage.py collectstatic --noinput
python manage.py check --deploy
```

## Common Issues

- **Missing manifest**: ensure `vite build` runs with `manifest: true`.
- **404 static assets**: verify `collectstatic` output and static web server path.
- **Dev server URLs in production HTML**: ensure `HYPER_DEV = False`.
- **Wrong output path**: `HYPER_VITE_OUTPUT_DIR` and Vite output must match.
