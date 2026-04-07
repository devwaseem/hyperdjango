from __future__ import annotations

from pathlib import Path

import pytest

from hyperdjango.routing.compiler import compile_routes


PAGE_TEMPLATE = """from hyperdjango.page import Page


class DemoPage(Page):
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
