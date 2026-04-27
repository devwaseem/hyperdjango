from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

from hyperdjango.conf import get_vite_output_dir


class ManifestEntry(NamedTuple):
    name: str
    file: str
    src: str = ""
    is_entry: bool = False
    is_dynamic_entry: bool = False
    import_list: list[str] = []
    asset_list: list[str] = []
    css_list: list[str] = []


@cache
def load_manifest() -> dict[str, ManifestEntry]:
    output_dir: Path = get_vite_output_dir()
    manifest_path = output_dir / ".vite" / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(
            f"Vite manifest not found at {manifest_path}. Run your Vite build first."
        )

    raw = json.loads(manifest_path.read_text())
    entries: dict[str, ManifestEntry] = {}
    for file_name, payload in raw.items():
        data = dict(payload)
        entries[file_name] = ManifestEntry(
            name=data["name"],
            file=data["file"],
            src=data.get("src", ""),
            is_entry=data.get("isEntry", False),
            is_dynamic_entry=data.get("isDynamicEntry", False),
            import_list=data.get("imports", []),
            asset_list=data.get("assets", []),
            css_list=data.get("css", []),
        )
    return entries
