from __future__ import annotations

import json
from pathlib import Path

from hyperdjango.management.commands.hyper_scaffold import (
    LAYOUT_PY,
    VITE_CONFIG,
    _ensure_package_json,
    _merge_package_json,
    _wire_settings,
    _wire_urls,
)


def test_merge_package_json_adds_missing_hyper_defaults() -> None:
    payload = {
        "name": "my-app",
        "scripts": {"test": "pytest"},
        "dependencies": {"react": "19.0.0"},
    }

    merged = _merge_package_json(payload)

    assert merged["name"] == "my-app"
    assert merged["scripts"]["test"] == "pytest"
    assert merged["scripts"]["dev"] == "vite"
    assert merged["scripts"]["build"] == "vite build"
    assert merged["dependencies"]["react"] == "19.0.0"
    assert merged["dependencies"]["alpinejs"] == "^3.14.9"
    assert merged["devDependencies"]["vite"] == "^7.0.0"


def test_ensure_package_json_creates_and_updates(tmp_path: Path) -> None:
    path = tmp_path / "package.json"

    created = _ensure_package_json(path)
    assert created == "created"

    payload = json.loads(path.read_text())
    assert payload["scripts"]["dev"] == "vite"

    path.write_text(json.dumps({"name": "x", "scripts": {}}, indent=2) + "\n")
    updated = _ensure_package_json(path)
    assert updated == "updated"
    payload = json.loads(path.read_text())
    assert payload["scripts"]["build"] == "vite build"


def test_wire_settings_is_idempotent(tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.py"
    settings_file.write_text(
        "BASE_DIR = Path(__file__).resolve().parent\n"
        "DEBUG = True\n"
        "INSTALLED_APPS = []\n"
        'TEMPLATES = [{"DIRS": []}]\n'
    )

    changed_first = _wire_settings(settings_file)
    changed_second = _wire_settings(settings_file)

    content = settings_file.read_text()
    assert changed_first is True
    assert changed_second is False
    assert 'HYPER_FRONTEND_DIR = BASE_DIR / "hyper"' in content
    assert 'INSTALLED_APPS.append("hyperdjango")' in content


def test_wire_urls_is_idempotent(tmp_path: Path) -> None:
    urls_file = tmp_path / "urls.py"
    urls_file.write_text(
        "from django.urls import path\n"
        'urlpatterns = [path("admin/", lambda request: None)]\n'
    )

    changed_first = _wire_urls(urls_file)
    changed_second = _wire_urls(urls_file)

    content = urls_file.read_text()
    assert changed_first is True
    assert changed_second is False
    assert "from hyperdjango.urls import include_routes" in content
    assert "urlpatterns = [*include_routes(), *urlpatterns]" in content


def test_scaffold_templates_and_hyperview_defaults() -> None:
    assert "from hyperdjango.page import HyperView" in LAYOUT_PY
    assert 'const templatesRoot = path.resolve("./hyper/templates");' in VITE_CONFIG
    assert '"@templates": templatesRoot' in VITE_CONFIG
