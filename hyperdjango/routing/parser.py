from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RouteSegment:
    raw: str
    kind: str
    name: str
    regex_part: str | None = None

    @property
    def path_part(self) -> str:
        if self.kind in {"group", "index"}:
            return ""
        if self.kind == "dynamic":
            return f"<{self.name}>"
        if self.kind == "catchall":
            return f"<path:{self.name}>"
        if self.kind == "pattern":
            return self.name
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
        if (
            "[" not in inner
            and "]" not in inner
            and inner.startswith("...")
            and len(inner) > 3
        ):
            return RouteSegment(raw=segment, kind="catchall", name=inner[3:])
        if "[" not in inner and "]" not in inner:
            return RouteSegment(raw=segment, kind="dynamic", name=inner)

    if "[" in segment and "]" in segment:
        regex_part = _parse_pattern_segment(segment)
        if regex_part is not None:
            return RouteSegment(
                raw=segment,
                kind="pattern",
                name=segment,
                regex_part=regex_part,
            )

    return RouteSegment(raw=segment, kind="static", name=segment)


def build_django_route(segments: list[RouteSegment]) -> str:
    parts = [segment.path_part for segment in segments if segment.path_part]
    return "/".join(parts)


def build_regex_route(segments: list[RouteSegment]) -> str:
    parts: list[str] = []
    for segment in segments:
        if segment.kind in {"group", "index"}:
            continue
        if segment.kind == "static":
            parts.append(re.escape(segment.name))
            continue
        if segment.kind == "dynamic":
            parts.append(f"(?P<{segment.name}>[^/]+)")
            continue
        if segment.kind == "catchall":
            parts.append(f"(?P<{segment.name}>.+)")
            continue
        if segment.kind == "pattern" and segment.regex_part:
            parts.append(segment.regex_part)
            continue
        parts.append(re.escape(segment.raw))
    body = "/".join(parts)
    return f"^{body}$"


def route_specificity(segments: list[RouteSegment]) -> tuple[int, int, int, int]:
    static_count = sum(1 for s in segments if s.kind == "static")
    dynamic_count = sum(1 for s in segments if s.kind in {"dynamic", "pattern"})
    catchall_count = sum(1 for s in segments if s.kind == "catchall")
    total_parts = len([s for s in segments if s.kind not in {"group", "index"}])
    return (catchall_count, dynamic_count, -static_count, -total_parts)


def _parse_pattern_segment(segment: str) -> str | None:
    token_re = re.compile(r"\[([a-zA-Z_][a-zA-Z0-9_]*)\]")
    index = 0
    parts: list[str] = []
    seen_names: set[str] = set()
    matched = False

    for match in token_re.finditer(segment):
        matched = True
        start, end = match.span()
        if start > index:
            parts.append(re.escape(segment[index:start]))
        name = match.group(1)
        if name in seen_names:
            return None
        seen_names.add(name)
        parts.append(f"(?P<{name}>[^/]+)")
        index = end

    if not matched:
        return None
    if index < len(segment):
        parts.append(re.escape(segment[index:]))

    leftover = token_re.sub("", segment)
    if "[" in leftover or "]" in leftover:
        return None

    return "".join(parts)
