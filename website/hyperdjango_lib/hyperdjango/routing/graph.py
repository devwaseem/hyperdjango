from __future__ import annotations

from dataclasses import dataclass

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
            skeleton = _pattern_skeleton(segment.raw)
            normalized_parts.append(f"p:{skeleton}")

    return RouteKey(path="/".join(normalized_parts), shape=tuple(shape))


def _pattern_skeleton(raw: str) -> str:
    parts: list[str] = []
    idx = 0
    while idx < len(raw):
        if raw[idx] != "[":
            parts.append(raw[idx])
            idx += 1
            continue

        end = _find_closing_bracket(raw, idx)
        if end is None:
            parts.append(raw[idx])
            idx += 1
            continue
        parts.append("[]")
        idx = end + 1

    return "".join(parts)


def _find_closing_bracket(text: str, open_index: int) -> int | None:
    depth = 0
    idx = open_index + 1
    while idx < len(text):
        ch = text[idx]
        if ch == "[":
            depth += 1
        elif ch == "]":
            if depth == 0:
                return idx
            depth -= 1
        idx += 1
    return None
