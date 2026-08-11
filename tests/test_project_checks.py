from __future__ import annotations

import os
from pathlib import Path

from django.test import override_settings

from hyperdjango.checks import check_hyperdjango_project


def _ids(messages) -> set[str]:
    return {message.id for message in messages}


def test_project_check_reports_missing_production_manifest(tmp_path: Path) -> None:
    frontend = tmp_path / "hyper"
    frontend.mkdir()
    (tmp_path / "vite.config.js").write_text("export default {}\n")

    with override_settings(
        BASE_DIR=tmp_path,
        HYPER_FRONTEND_DIR=frontend,
        HYPER_VITE_OUTPUT_DIR=tmp_path / "dist",
        HYPER_DEV=False,
    ):
        messages = check_hyperdjango_project(None)

    assert "hyperdjango.E006" in _ids(messages)


def test_project_check_reports_stale_production_manifest(tmp_path: Path) -> None:
    frontend = tmp_path / "hyper"
    entry = frontend / "routes" / "index" / "entry.ts"
    entry.parent.mkdir(parents=True)
    entry.write_text("export {}\n")
    manifest = tmp_path / "dist" / ".vite" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}\n")
    os.utime(manifest, (1, 1))
    os.utime(entry, (2, 2))

    with override_settings(
        BASE_DIR=tmp_path,
        HYPER_FRONTEND_DIR=frontend,
        HYPER_VITE_OUTPUT_DIR=tmp_path / "dist",
        HYPER_DEV=False,
    ):
        messages = check_hyperdjango_project(None)

    assert "hyperdjango.W002" in _ids(messages)


def test_devtools_runtime_uses_vite_overlay_for_django_500s() -> None:
    runtime = (
        Path(__file__).resolve().parents[1]
        / "hyperdjango/static/hyperdjango/dev-toolbar.js"
    ).read_text()
    assert 'import(`${viteUrl}@vite/client`)' in runtime
    assert "new viteClient.ErrorOverlay" in runtime
