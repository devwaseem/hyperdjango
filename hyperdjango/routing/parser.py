from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteSegment:
    raw: str
    kind: str
    name: str

    @property
    def path_part(self) -> str:
        if self.kind in {"group", "index"}:
            return ""
        if self.kind == "dynamic":
            return f"<{self.name}>"
        if self.kind == "catchall":
            return f"<path:{self.name}>"
        return self.name


def parse_segment(segment: str) -> RouteSegment:
    if not segment:
        raise ValueError("Route segment cannot be empty")

    if segment == "index":
        return RouteSegment(raw=segment, kind="index", name="index")

    if segment.startswith("(") and segment.endswith(")") and len(segment) > 2:
        return RouteSegment(raw=segment, kind="group", name=segment[1:-1])

    if segment.startswith("[") and segment.endswith("]") and len(segment) > 2:
        inner = segment[1:-1]
        if inner.startswith("...") and len(inner) > 3:
            return RouteSegment(raw=segment, kind="catchall", name=inner[3:])
        return RouteSegment(raw=segment, kind="dynamic", name=inner)

    return RouteSegment(raw=segment, kind="static", name=segment)


def build_django_route(segments: list[RouteSegment]) -> str:
    parts = [segment.path_part for segment in segments if segment.path_part]
    return "/".join(parts)


def route_specificity(segments: list[RouteSegment]) -> tuple[int, int, int, int]:
    static_count = sum(1 for s in segments if s.kind == "static")
    dynamic_count = sum(1 for s in segments if s.kind == "dynamic")
    catchall_count = sum(1 for s in segments if s.kind == "catchall")
    total_parts = len([s for s in segments if s.kind not in {"group", "index"}])
    return (catchall_count, dynamic_count, -static_count, -total_parts)
