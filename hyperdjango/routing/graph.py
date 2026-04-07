from __future__ import annotations

from dataclasses import dataclass
import re

from hyperdjango.routing.parser import RouteSegment


@dataclass(frozen=True)
class RouteKey:
    path: str
    shape: tuple[str, ...]


def make_route_key(segments: list[RouteSegment]) -> RouteKey:
    normalized_parts: list[str] = []
    shape: list[str] = []

    for segment in segments:
        if segment.kind in {"group", "index"}:
            continue

        shape.append(segment.kind)
        if segment.kind == "static":
            normalized_parts.append(f"s:{segment.name}")
        elif segment.kind == "dynamic":
            normalized_parts.append("d")
        elif segment.kind == "catchall":
            normalized_parts.append("c")
        elif segment.kind == "pattern":
            skeleton = re.sub(r"\[[^\]]+\]", "[]", segment.raw)
            normalized_parts.append(f"p:{skeleton}")

    return RouteKey(path="/".join(normalized_parts), shape=tuple(shape))
