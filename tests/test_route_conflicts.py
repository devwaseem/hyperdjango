from __future__ import annotations

from pathlib import Path

import pytest

from hyperdjango.routing.compiler import compile_routes
from hyperdjango.routing.loader import RouteLoadError


PAGE_TEMPLATE = """from hyperdjango.page import HyperView


class PageView(HyperView):
    pass
"""


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_conflict_for_group_and_plain_same_path(tmp_path: Path) -> None:
    routes_dir = tmp_path / "frontend" / "routes"
    _write(routes_dir / "(marketing)" / "pricing" / "page.py", PAGE_TEMPLATE)
    _write(routes_dir / "pricing" / "page.py", PAGE_TEMPLATE)

    with pytest.raises(RuntimeError, match="Route conflict detected"):
        compile_routes(routes_dir)


def test_conflict_for_same_path_shape_with_different_param_names(
    tmp_path: Path,
) -> None:
    routes_dir = tmp_path / "frontend" / "routes"
    _write(routes_dir / "blog" / "[slug]" / "page.py", PAGE_TEMPLATE)
    _write(routes_dir / "blog" / "[id]" / "page.py", PAGE_TEMPLATE)

    with pytest.raises(RuntimeError, match="Route conflict detected"):
        compile_routes(routes_dir)


def test_templates_folder_page_files_are_not_routed(tmp_path: Path) -> None:
    routes_dir = tmp_path / "frontend" / "routes"
    templates_dir = tmp_path / "frontend" / "templates"
    _write(routes_dir / "home" / "page.py", PAGE_TEMPLATE)
    _write(templates_dir / "profile_card" / "page.py", PAGE_TEMPLATE)

    compiled = compile_routes(routes_dir)

    assert len(compiled) == 1
    assert compiled[0].django_path == "home"


def test_route_page_requires_pageview_class_name(tmp_path: Path) -> None:
    routes_dir = tmp_path / "frontend" / "routes"
    _write(
        routes_dir / "home" / "page.py",
        """from hyperdjango.page import HyperView\n\n\nclass HomePage(HyperView):\n    pass\n""",
    )

    with pytest.raises(RouteLoadError, match="PageView"):
        compile_routes(routes_dir)
