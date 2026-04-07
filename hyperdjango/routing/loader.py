from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import TypeVar

from hyperdjango.page import HyperView


TPage = TypeVar("TPage", bound=type[HyperView])


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


def find_page_class(module: ModuleType) -> type[HyperView]:
    for value in vars(module).values():
        if (
            isinstance(value, type)
            and issubclass(value, HyperView)
            and value is not HyperView
            and value.__module__ == module.__name__
        ):
            return value
    raise RouteLoadError(f"No HyperView subclass found in {module.__name__}")


def find_layout_class(module: ModuleType) -> type[HyperView]:
    return find_page_class(module)
