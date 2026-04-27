from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

from hyperdjango.page import HyperView


TPage = TypeVar("TPage", bound=type[Any])


class RouteLoadError(Exception):
    pass


def load_module_from_path(file_path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RouteLoadError(f"Cannot import module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def find_page_class(module: ModuleType) -> type[Any]:
    page_view = getattr(module, "PageView", None)
    if isinstance(page_view, type) and page_view.__module__ == module.__name__:
        return page_view

    module_file = getattr(module, "__file__", None) or "<unknown file>"
    raise RouteLoadError(
        f"No PageView class found in {module_file}. "
        "Route modules must define `class PageView(...)`"
    )
