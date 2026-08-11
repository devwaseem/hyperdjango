from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Warning, register


ENTRY_NAMES = {
    "entry.ts",
    "entry.js",
    "entry.head.ts",
    "entry.head.js",
}


def _frontend_dir() -> Path | None:
    value = getattr(settings, "HYPER_FRONTEND_DIR", None)
    return Path(value) if value else None


def _entry_files(frontend_dir: Path) -> list[Path]:
    return [
        path
        for path in frontend_dir.rglob("*")
        if path.name in ENTRY_NAMES
        or path.name.endswith((".entry.ts", ".entry.js"))
    ]


@register()
def check_hyperdjango_project(app_configs, **kwargs):
    del app_configs, kwargs
    messages = []
    frontend_dir = _frontend_dir()
    if frontend_dir is None:
        return [
            Error(
                "HYPER_FRONTEND_DIR is not configured.",
                hint="Set HYPER_FRONTEND_DIR = BASE_DIR / 'hyper'.",
                id="hyperdjango.E001",
            )
        ]
    if not frontend_dir.is_dir():
        return [
            Error(
                f"HYPER_FRONTEND_DIR does not exist: {frontend_dir}",
                hint="Create it with `python manage.py hyper_scaffold` or correct the setting.",
                id="hyperdjango.E002",
            )
        ]

    routes_dir = frontend_dir / "routes"
    if routes_dir.is_dir():
        try:
            from hyperdjango.routing.compiler import compile_routes

            compile_routes(routes_dir)
        except Exception as exc:
            messages.append(
                Error(
                    f"HyperDjango routes could not be compiled: {exc}",
                    hint="Run `python manage.py hyper_routes` for the conflicting file or import.",
                    id="hyperdjango.E003",
                )
            )

    entries = _entry_files(frontend_dir)
    broken_entries = [path for path in entries if path.is_symlink() and not path.exists()]
    for path in broken_entries:
        messages.append(
            Error(
                f"Colocated Vite entry is a broken link: {path}",
                hint="Restore the entry target or remove the dangling link.",
                id="hyperdjango.E004",
            )
        )

    dev_mode = bool(getattr(settings, "HYPER_DEV", getattr(settings, "DEBUG", False)))
    base_dir = Path(getattr(settings, "BASE_DIR", frontend_dir.parent))
    if dev_mode:
        if not any((base_dir / name).is_file() for name in ("vite.config.js", "vite.config.ts")):
            messages.append(
                Warning(
                    f"No Vite configuration was found in {base_dir}.",
                    hint="Run `python manage.py hyper_scaffold` or add vite.config.js.",
                    id="hyperdjango.W001",
                )
            )
        return messages

    output_value = getattr(settings, "HYPER_VITE_OUTPUT_DIR", None)
    if not output_value:
        messages.append(
            Error(
                "HYPER_VITE_OUTPUT_DIR is not configured for production.",
                hint="Set it to the directory produced by `vite build`.",
                id="hyperdjango.E005",
            )
        )
        return messages
    manifest = Path(output_value) / ".vite" / "manifest.json"
    if not manifest.is_file():
        messages.append(
            Error(
                f"Vite production manifest is missing: {manifest}",
                hint="Run your package manager's build command before deploying.",
                id="hyperdjango.E006",
            )
        )
        return messages
    newest_entry = max(
        (path.stat().st_mtime for path in entries if path.exists()), default=0
    )
    if newest_entry > manifest.stat().st_mtime:
        messages.append(
            Warning(
                "The Vite manifest is older than a colocated frontend entry.",
                hint="Run the Vite production build again.",
                id="hyperdjango.W002",
            )
        )
    return messages
