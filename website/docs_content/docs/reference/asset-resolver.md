# Asset Resolver Reference

HyperDjango automatically resolves assets compiled by Vite. The behavior differs based on whether the application is running in development or production.

## Modes of Operation

The system detects the environment using `is_dev_env()` (typically based on `DEBUG` or `HYPER_DEV` settings).

### Development Mode (`HYPER_DEV=True` or `DEBUG=True`)

In this mode, assets are served directly by the Vite development server.

- **Resolver**: `ViteDevServerAssetResolver`
- **Behavior**: 
  - Resolves imports to the Vite dev server URL (default: `http://localhost:5173/`).
  - Returns a single `ModuleTag` for requested entries.
  - Vite handles all internal module resolution and HMR (Hot Module Replacement) automatically.

### Production Mode (Manifest Mode)

In this mode, HyperDjango uses a pre-generated `.vite/manifest.json` file to map source entries to built asset files.

- **Resolver**: `ManifestAssetResolver`
- **Behavior**:
  - Requires a successful Vite build (manifest must exist at `<output_dir>/.vite/manifest.json`).
  - Resolves entries by looking up the key in the manifest.
  - Returns a sequence of:
    1. `ModulePreloadTag`s for all transitive JS imports.
    2. `StyleSheetTag`s for associated CSS.
    3. The main `ModuleTag` for the entry point itself.

## Manifest File Format

HyperDjango parses Vite's standard manifest JSON.

```json
{
  "src/entry.js": {
    "file": "assets/entry-a1b2c3d4.js",
    "src": "src/entry.js",
    "isEntry": true,
    "imports": ["src/lib.js"],
    "css": ["assets/entry-e5f6g7h8.css"]
  }
}
```

The resolver maps this to a `ManifestEntry` object containing:
- `file`: The final hashed filename.
- `import_list`: References to other JS files for preloading.
- `css_list`: CSS files to link.

## Asset Tags

The system uses specific tag classes for rendering:

| Tag Type | HTML Output |
| :--- | :--- |
| `ModuleTag` | `<script type="module" src="..."></script>` |
| `StyleSheetTag` | `<link rel="stylesheet" href="...">` |
| `ModulePreloadTag`| `<link rel="modulepreload" href="...">` |
