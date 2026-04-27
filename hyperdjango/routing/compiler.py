from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from django.http import HttpRequest, HttpResponse
from django.urls import path, re_path
from django.views import View

from hyperdjango.conf import get_append_slash
from hyperdjango.page import HyperView
from hyperdjango.routing.graph import make_route_key
from hyperdjango.routing.parser import (
    RouteSegment,
    build_regex_route,
    parse_segment,
)
from hyperdjango.routing.loader import (
    find_page_class,
    load_module_from_path,
)
from hyperdjango.routing.parser import build_django_route, route_specificity
from hyperdjango.routing.scanner import scan_route_files


@dataclass(frozen=True)
class CompiledRoute:
    django_path: str
    page_class: type[Any]
    view_name: str
    regex_path: str | None = None


def compose_page_class(page_class: type[Any], layouts: list[type[Any]]) -> type[Any]:
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


def build_route_view(page_class: type[Any]) -> Callable[..., HttpResponse]:
    if issubclass(page_class, HyperView):

        def view(request: HttpRequest, **kwargs: str) -> HttpResponse:
            page = page_class()
            return page.dispatch(request, **kwargs)

        return view

    if issubclass(page_class, View):
        return page_class.as_view()

    def view(request: HttpRequest, **kwargs: str) -> HttpResponse:
        page = page_class()
        return page.dispatch(request, **kwargs)

    return view


def compile_routes(routes_dir: Path, *, url_prefix: str = "") -> list[CompiledRoute]:
    route_files = scan_route_files(routes_dir)
    compiled: list[CompiledRoute] = []
    seen_paths: dict[str, tuple[tuple[str, ...], Path, str]] = {}
    append_slash = get_append_slash()

    for route_file in route_files:
        prefix_segments = [
            parse_segment(part) for part in url_prefix.split("/") if part.strip()
        ]
        all_segments = [*prefix_segments, *route_file.segments]
        key = make_route_key(all_segments)
        display_path = (
            build_django_route(all_segments, append_slash=append_slash) or "/"
        )
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

        effective_page_class = compose_page_class(page_class, [])
        route_path = build_django_route(all_segments, append_slash=append_slash)
        regex_path = (
            build_regex_route(all_segments, append_slash=append_slash)
            if any(segment.kind == "pattern" for segment in all_segments)
            else None
        )

        compiled.append(
            CompiledRoute(
                django_path=route_path,
                page_class=effective_page_class,
                view_name=_view_name(all_segments, page_class),
                regex_path=regex_path,
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
        if item.regex_path:
            urlpatterns.append(
                re_path(
                    item.regex_path,
                    build_route_view(item.page_class),
                    name=item.view_name,
                )
            )
        else:
            urlpatterns.append(
                path(
                    item.django_path,
                    build_route_view(item.page_class),
                    name=item.view_name,
                )
            )
    return urlpatterns


def _module_name(file_path: Path) -> str:
    digest = hashlib.md5(str(file_path).encode(), usedforsecurity=False).hexdigest()
    stem = re.sub(r"[^0-9A-Za-z_]+", "_", file_path.stem)
    return f"hyperdjango.dynamic.{stem}.{digest}"


def _view_name(segments: list[RouteSegment], page_class: type[Any]) -> str:
    custom_name = getattr(page_class, "route_name", None)
    if isinstance(custom_name, str) and custom_name.strip():
        return custom_name.strip()

    parts: list[str] = []
    for segment in segments:
        if segment.kind in {"group", "index"}:
            continue
        if segment.kind == "catchall":
            parts.append(f"path_{segment.name}")
            continue
        if segment.kind == "pattern":
            if segment.param_names:
                parts.extend(segment.param_names)
            else:
                parts.append("pattern")
            continue
        parts.append(segment.name)

    if not parts:
        return "hyper_index"
    return f"hyper_{'_'.join(parts)}"


def _segments_from_route(route: str):
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
