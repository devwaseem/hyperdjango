from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.urls import path

from hyperdjango.page import Page
from hyperdjango.routing.graph import make_route_key
from hyperdjango.routing.loader import (
    find_layout_class,
    find_page_class,
    load_module_from_path,
)
from hyperdjango.routing.parser import build_django_route, route_specificity
from hyperdjango.routing.scanner import discover_layout_files, scan_route_files


@dataclass(frozen=True)
class CompiledRoute:
    django_path: str
    page_class: type[Page]
    view_name: str


def compose_page_class(page_class: type[Page], layouts: list[type[Page]]) -> type[Page]:
    if not layouts:
        return page_class

    missing_layouts = [
        layout for layout in layouts if not issubclass(page_class, layout)
    ]
    if not missing_layouts:
        return page_class

    bases = tuple([page_class, *reversed(missing_layouts)])
    class_name = f"Composed{page_class.__name__}"
    return type(class_name, bases, {"__module__": page_class.__module__})


def build_route_view(page_class: type[Page]) -> Callable[..., HttpResponse]:
    def view(request: HttpRequest, **kwargs: str) -> HttpResponse:
        page = page_class()
        return page.dispatch(request, **kwargs)

    return view


def compile_routes(routes_dir: Path, *, url_prefix: str = "") -> list[CompiledRoute]:
    route_files = scan_route_files(routes_dir)
    compiled: list[CompiledRoute] = []
    seen_paths: dict[str, tuple[tuple[str, ...], Path, str]] = {}

    for route_file in route_files:
        key = make_route_key(route_file.segments)
        display_path = build_django_route(route_file.segments) or "/"
        if key.path in seen_paths:
            previous_shape, previous_file, previous_display_path = seen_paths[key.path]
            raise RuntimeError(
                "Route conflict detected for "
                f"'{display_path}' (conflicts with '{previous_display_path}'): "
                f"{previous_file} (shape={previous_shape}) "
                f"and {route_file.page_file} (shape={key.shape})"
            )

        page_module_name = _module_name(route_file.page_file)
        page_module = load_module_from_path(route_file.page_file, page_module_name)
        page_class = find_page_class(page_module)

        layout_classes: list[type[Page]] = []
        for layout_file in discover_layout_files(route_file.directory, routes_dir):
            module_name = _module_name(layout_file)
            module = load_module_from_path(layout_file, module_name)
            layout_classes.append(find_layout_class(module))

        effective_page_class = compose_page_class(page_class, layout_classes)
        route_path = build_django_route(route_file.segments)
        if url_prefix:
            route_path = "/".join([url_prefix.strip("/"), route_path]).strip("/")

        compiled.append(
            CompiledRoute(
                django_path=route_path,
                page_class=effective_page_class,
                view_name=_view_name(route_file.page_file),
            )
        )
        seen_paths[key.path] = (key.shape, route_file.page_file, display_path)

    compiled.sort(
        key=lambda item: route_specificity(_segments_from_route(item.django_path))
    )
    return compiled


def build_urlpatterns(routes_dir: Path, *, url_prefix: str = "") -> list:
    compiled = compile_routes(routes_dir, url_prefix=url_prefix)
    urlpatterns = []
    for item in compiled:
        urlpatterns.append(
            path(
                item.django_path, build_route_view(item.page_class), name=item.view_name
            )
        )
    return urlpatterns


def _module_name(file_path: Path) -> str:
    digest = hashlib.md5(str(file_path).encode(), usedforsecurity=False).hexdigest()
    return f"hyperdjango.dynamic.{file_path.stem}.{digest}"


def _view_name(file_path: Path) -> str:
    name = "_".join(file_path.parts[-3:]).replace(".py", "")
    return f"hyper_{name}"


def _segments_from_route(route: str):
    from hyperdjango.routing.parser import parse_segment

    if not route:
        return []
    result = []
    for part in route.split("/"):
        if not part:
            continue
        if part.startswith("<path:") and part.endswith(">"):
            result.append(parse_segment(f"[...{part[6:-1]}]"))
        elif part.startswith("<") and part.endswith(">"):
            result.append(parse_segment(f"[{part[1:-1]}]"))
        else:
            result.append(parse_segment(part))
    return result
