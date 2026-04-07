from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hyperdjango.routing.parser import RouteSegment, parse_segment


@dataclass(frozen=True)
class RouteFile:
    page_file: Path
    directory: Path
    segments: list[RouteSegment]


def scan_route_files(routes_dir: Path) -> list[RouteFile]:
    if not routes_dir.exists() or not routes_dir.is_dir():
        raise RuntimeError(f"Route directory does not exist: {routes_dir}")

    route_files: list[RouteFile] = []
    for page_file in routes_dir.rglob("page.py"):
        directory = page_file.parent
        rel = directory.relative_to(routes_dir)
        raw_segments = [seg for seg in rel.parts if seg]
        segments = [parse_segment(seg) for seg in raw_segments]
        route_files.append(
            RouteFile(page_file=page_file, directory=directory, segments=segments)
        )
    return route_files


def discover_layout_files(route_dir: Path, routes_dir: Path) -> list[Path]:
    layouts: list[Path] = []
    current = route_dir
    while current != routes_dir and routes_dir in current.parents:
        layout_file = current / "layout.py"
        if layout_file.exists():
            layouts.append(layout_file)
        current = current.parent

    root_layout = routes_dir / "layout.py"
    if root_layout.exists():
        layouts.append(root_layout)
    layouts.reverse()
    return layouts
