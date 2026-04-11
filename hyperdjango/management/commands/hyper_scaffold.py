from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand


SCAFFOLD_MARKER_START = "# --- HyperDjango scaffold start ---"
SCAFFOLD_MARKER_END = "# --- HyperDjango scaffold end ---"


class Command(BaseCommand):
    help = "Scaffold HyperDjango files (dirs, Vite, package.json) for existing projects"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing scaffolded files",
        )
        parser.add_argument(
            "--no-wire",
            action="store_true",
            help="Do not patch Django settings/urls automatically",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        force = bool(options.get("force"))
        wire = not bool(options.get("no_wire"))

        base_dir = Path(settings.BASE_DIR)
        hyper_dir = base_dir / "hyper"
        routes_dir = hyper_dir / "routes"
        templates_dir = hyper_dir / "templates"
        layouts_dir = hyper_dir / "layouts"
        shared_dir = hyper_dir / "shared"

        created: list[str] = []
        updated: list[str] = []
        skipped: list[str] = []

        def write(path: Path, content: str) -> None:
            action = _write_file(path, content, force=force)
            rel = str(path.relative_to(base_dir))
            if action == "created":
                created.append(rel)
            elif action == "updated":
                updated.append(rel)
            else:
                skipped.append(rel)

        write(hyper_dir / "__init__.py", "")
        write(routes_dir / "__init__.py", "")
        write(templates_dir / "__init__.py", "")
        write(layouts_dir / "__init__.py", "")
        write(shared_dir / "__init__.py", "")

        write(layouts_dir / "base" / "__init__.py", LAYOUT_PY)
        write(layouts_dir / "base" / "index.html", LAYOUT_HTML)
        write(layouts_dir / "base" / "entry.ts", LAYOUT_ENTRY_TS)

        write(routes_dir / "index" / "+page.py", INDEX_PAGE_PY)
        write(routes_dir / "index" / "index.html", INDEX_HTML)
        write(templates_dir / "profile_card" / "page.py", TEMPLATE_PAGE_PY)
        write(templates_dir / "profile_card" / "index.html", TEMPLATE_INDEX_HTML)

        write(base_dir / "vite.config.js", VITE_CONFIG)

        package_json_action = _ensure_package_json(base_dir / "package.json")
        if package_json_action == "created":
            created.append("package.json")
        elif package_json_action == "updated":
            updated.append("package.json")
        else:
            skipped.append("package.json")

        gitignore_action = _ensure_gitignore(base_dir / ".gitignore")
        if gitignore_action == "created":
            created.append(".gitignore")
        elif gitignore_action == "updated":
            updated.append(".gitignore")
        else:
            skipped.append(".gitignore")

        if wire:
            settings_file = _resolve_module_file(settings.SETTINGS_MODULE)
            urls_file = _resolve_module_file(settings.ROOT_URLCONF)

            settings_action = _wire_settings(settings_file)
            urls_action = _wire_urls(urls_file)
            if settings_action:
                updated.append(str(settings_file.relative_to(base_dir)))
            else:
                skipped.append(str(settings_file.relative_to(base_dir)))
            if urls_action:
                updated.append(str(urls_file.relative_to(base_dir)))
            else:
                skipped.append(str(urls_file.relative_to(base_dir)))

        self.stdout.write("HyperDjango scaffold complete.")
        if created:
            self.stdout.write(f"Created: {', '.join(sorted(set(created)))}")
        if updated:
            self.stdout.write(f"Updated: {', '.join(sorted(set(updated)))}")
        if skipped:
            self.stdout.write(f"Skipped: {', '.join(sorted(set(skipped)))}")

        self.stdout.write("Next: run `npm install` then `npm run dev` for Vite assets.")


def _write_file(path: Path, content: str, *, force: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return "skipped"
    previous = path.exists()
    path.write_text(content)
    return "updated" if previous else "created"


def _resolve_module_file(module_name: str) -> Path:
    module = importlib.import_module(module_name)
    file_path = getattr(module, "__file__", "")
    if not file_path:
        raise RuntimeError(f"Could not resolve file for module: {module_name}")
    return Path(file_path)


def _wire_settings(path: Path) -> bool:
    text = path.read_text()
    if SCAFFOLD_MARKER_START in text:
        return False

    block = f"""

{SCAFFOLD_MARKER_START}
if "hyperdjango" not in INSTALLED_APPS:
    INSTALLED_APPS.append("hyperdjango")

HYPER_FRONTEND_DIR = BASE_DIR / "hyper"
HYPER_VITE_OUTPUT_DIR = BASE_DIR / "dist"
HYPER_VITE_DEV_SERVER_URL = "http://localhost:5173/"
HYPER_DEV = DEBUG

if HYPER_FRONTEND_DIR not in TEMPLATES[0]["DIRS"]:
    TEMPLATES[0]["DIRS"].append(HYPER_FRONTEND_DIR)

if "STATICFILES_DIRS" in globals():
    if HYPER_VITE_OUTPUT_DIR not in STATICFILES_DIRS:
        STATICFILES_DIRS.append(HYPER_VITE_OUTPUT_DIR)
else:
    STATICFILES_DIRS = [HYPER_VITE_OUTPUT_DIR]
{SCAFFOLD_MARKER_END}
"""

    path.write_text(text.rstrip() + block)
    return True


def _wire_urls(path: Path) -> bool:
    text = path.read_text()
    if SCAFFOLD_MARKER_START in text or "include_routes(" in text:
        return False

    block = f"""

{SCAFFOLD_MARKER_START}
from hyperdjango.urls import include_routes

urlpatterns = [*include_routes(), *urlpatterns]
{SCAFFOLD_MARKER_END}
"""
    path.write_text(text.rstrip() + block)
    return True


def _ensure_gitignore(path: Path) -> str:
    required_entries = [
        "node_modules/",
        "dist/",
    ]
    if not path.exists():
        path.write_text("\n".join(required_entries) + "\n")
        return "created"

    lines = path.read_text().splitlines()
    existing = set(line.strip() for line in lines)
    missing = [entry for entry in required_entries if entry not in existing]
    if not missing:
        return "skipped"

    content = path.read_text().rstrip("\n") + "\n"
    content += "\n# HyperDjango\n" + "\n".join(missing) + "\n"
    path.write_text(content)
    return "updated"


def _ensure_package_json(path: Path) -> str:
    desired = _desired_package_json()
    if not path.exists():
        path.write_text(json.dumps(desired, indent=2) + "\n")
        return "created"

    payload = json.loads(path.read_text())
    merged = _merge_package_json(payload)
    if merged == payload:
        return "skipped"

    path.write_text(json.dumps(merged, indent=2) + "\n")
    return "updated"


def _desired_package_json() -> dict[str, Any]:
    return {
        "name": "hyperdjango-app",
        "private": True,
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
        },
        "devDependencies": {
            "vite": "^7.0.0",
        },
        "dependencies": {
            "@alpinejs/morph": "^3.14.9",
            "alpinejs": "^3.14.9",
            "morphdom": "^2.7.4",
            "vanilla-sonner": "^0.5.2",
        },
    }


def _merge_package_json(payload: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)

    if "private" not in merged:
        merged["private"] = True
    if "type" not in merged:
        merged["type"] = "module"

    scripts = dict(merged.get("scripts") or {})
    scripts.setdefault("dev", "vite")
    scripts.setdefault("build", "vite build")
    merged["scripts"] = scripts

    deps = dict(merged.get("dependencies") or {})
    for key, value in _desired_package_json()["dependencies"].items():
        deps.setdefault(key, value)
    merged["dependencies"] = deps

    dev_deps = dict(merged.get("devDependencies") or {})
    for key, value in _desired_package_json()["devDependencies"].items():
        dev_deps.setdefault(key, value)
    merged["devDependencies"] = dev_deps

    return merged


LAYOUT_PY = """from typing import Any, override

from django.http import HttpRequest

from hyperdjango.page import HyperView


class BaseLayout(HyperView):
    def __init__(self) -> None:
        super().__init__()
        self.title = "HyperDjango"

    @override
    def get_context(self, request: HttpRequest) -> dict[str, Any]:
        context = super().get_context(request)
        context["title"] = self.title
        return context
"""


LAYOUT_HTML = """{% extends \"hyperdjango/base.html\" %}
{% block body %}
<main>{% block page %}{% endblock page %}</main>
{% endblock body %}
"""


LAYOUT_ENTRY_TS = """import Alpine from \"alpinejs\";
import morph from \"@alpinejs/morph\";
import morphdom from \"morphdom\";

Alpine.plugin(morph);

if (!(window as any).Alpine) {
  (window as any).Alpine = Alpine;
}

// Hyper core prefers Alpine.morph when Alpine is present.
// Keep morphdom available as the non-Alpine fallback.
if (!(window as any).morphdom) {
  (window as any).morphdom = morphdom;
}

Alpine.start();
"""


INDEX_PAGE_PY = """from hyperdjango.actions import action
from hyperdjango.integrations.alpine.actions import Signal
from hyper.layouts.base import BaseLayout


class PageView(BaseLayout):
    def get(self, request):
        return {\"message\": \"Welcome to HyperDjango\"}

    @action
    def counter(self, request, count=0):
        return [Signal(name=\"count\", value=int(count) + 1)]
"""


INDEX_HTML = """{% extends \"layouts/base/index.html\" %}

{% block page %}
<section x-data=\"{ count: 0 }\">
  <h1>{{ message }}</h1>
  <p>Count: <span x-text=\"count\"></span></p>
  <button x-on:click=\"$action('counter', { count })\">Increment Signal</button>
</section>
{% endblock page %}
"""


VITE_CONFIG = """import fs from \"node:fs\";
import path from \"node:path\";
import { defineConfig, loadEnv } from \"vite\";

function walk(dir) {
  const output = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      output.push(...walk(full));
      continue;
    }
    output.push(full);
  }
  return output;
}

function discoverInputs(baseDirs) {
  const entries = {};
  for (const baseDir of baseDirs) {
    if (!fs.existsSync(baseDir)) {
      continue;
    }
    for (const file of walk(baseDir)) {
      const name = path.basename(file);
      const isEntry =
        name === \"entry.ts\" ||
        name === \"entry.js\" ||
        name === \"entry.head.ts\" ||
        name === \"entry.head.js\" ||
        name.endsWith(\".entry.ts\") ||
        name.endsWith(\".entry.js\");
      if (!isEntry) {
        continue;
      }
      const rel = path.relative(process.cwd(), file).replace(/\\\\/g, \"/\");
      entries[rel] = file;
    }
  }
  return entries;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());
  const routesRoot = path.resolve(\"./hyper/routes\");
  const templatesRoot = path.resolve(\"./hyper/templates\");
  const layoutsRoot = path.resolve(\"./hyper/layouts\");
  const sharedRoot = path.resolve(\"./hyper/shared\");
  const inputs = discoverInputs([routesRoot, templatesRoot, layoutsRoot, sharedRoot]);

  return {
    root: \".\",
    resolve: {
      alias: {
        \"@routes\": routesRoot,
        \"@templates\": templatesRoot,
        \"@layouts\": layoutsRoot,
        \"@shared\": sharedRoot,
      },
    },
    build: {
      outDir: env.VITE_APP_OUTPUT_DIR || \"./dist\",
      emptyOutDir: true,
      manifest: true,
      rollupOptions: {
        input: inputs,
      },
    },
  };
});
"""


TEMPLATE_PAGE_PY = """from hyperdjango.page import HyperPageTemplate


class ProfileCardTemplate(HyperPageTemplate):
    pass
"""


TEMPLATE_INDEX_HTML = """<article>
  <h2>{{ title|default:\"Profile\" }}</h2>
  <p>{{ description|default:\"Reusable template package\" }}</p>
</article>
"""
