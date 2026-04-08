from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast


KNOWN_CONVERTERS: dict[str, str] = {
    "str": r"[^/]+",
    "int": r"[0-9]+",
    "slug": r"[-a-zA-Z0-9_]+",
    "uuid": r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    "path": r".+",
}


@dataclass(frozen=True)
class RouteSegment:
    raw: str
    kind: str
    name: str
    converter: str | None = None
    regex_part: str | None = None
    param_names: tuple[str, ...] = ()

    @property
    def path_part(self) -> str:
        if self.kind in {"group", "index"}:
            return ""
        if self.kind == "dynamic":
            if self.converter:
                return f"<{self.converter}:{self.name}>"
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

    token_content = _extract_single_token_content(segment)
    if token_content is not None:
        token = _parse_token_content(token_content)
        if token["kind"] == "catchall":
            return RouteSegment(raw=segment, kind="catchall", name=token["name"])
        if token["kind"] == "dynamic":
            return RouteSegment(
                raw=segment,
                kind="dynamic",
                name=token["name"],
                converter=token.get("converter"),
            )
        if token["kind"] == "regex":
            return RouteSegment(
                raw=segment,
                kind="pattern",
                name=segment,
                regex_part=f"(?P<{token['name']}>{token['regex']})",
                param_names=(token["name"],),
            )

    if "[" in segment and "]" in segment:
        parsed = _parse_pattern_segment(segment)
        if parsed is not None:
            regex_part, param_names = cast(tuple[str, list[str]], parsed)
            return RouteSegment(
                raw=segment,
                kind="pattern",
                name=segment,
                regex_part=regex_part,
                param_names=tuple(param_names),
            )

    return RouteSegment(raw=segment, kind="static", name=segment)


def build_django_route(
    segments: list[RouteSegment], *, append_slash: bool = True
) -> str:
    parts = [segment.path_part for segment in segments if segment.path_part]
    if not parts:
        return ""
    route = "/".join(parts)
    if append_slash:
        return f"{route}/"
    return route


def build_regex_route(
    segments: list[RouteSegment], *, append_slash: bool = True
) -> str:
    parts: list[str] = []
    for segment in segments:
        if segment.kind in {"group", "index"}:
            continue
        if segment.kind == "static":
            parts.append(re.escape(segment.name))
            continue
        if segment.kind == "dynamic":
            if segment.converter and segment.converter in KNOWN_CONVERTERS:
                parts.append(
                    f"(?P<{segment.name}>{KNOWN_CONVERTERS[segment.converter]})"
                )
            else:
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
    if not body:
        return r"^$"
    if append_slash:
        return f"^{body}/$"
    return f"^{body}$"


def route_specificity(segments: list[RouteSegment]) -> tuple[int, int, int, int]:
    static_count = sum(1 for s in segments if s.kind == "static")
    dynamic_count = sum(1 for s in segments if s.kind in {"dynamic", "pattern"})
    catchall_count = sum(1 for s in segments if s.kind == "catchall")
    total_parts = len([s for s in segments if s.kind not in {"group", "index"}])
    return (catchall_count, dynamic_count, -static_count, -total_parts)


def _parse_pattern_segment(segment: str) -> tuple[str, list[str]] | None:
    index = 0
    parts: list[str] = []
    param_names: list[str] = []

    while index < len(segment):
        ch = segment[index]
        if ch != "[":
            next_open = segment.find("[", index)
            if next_open == -1:
                parts.append(re.escape(segment[index:]))
                break
            parts.append(re.escape(segment[index:next_open]))
            index = next_open
            continue

        token_end = _find_closing_bracket(segment, index)
        if token_end is None:
            return None

        token_content = segment[index + 1 : token_end]
        token = _parse_token_content(token_content)

        if token["kind"] == "catchall":
            return None

        if token["kind"] == "dynamic":
            name = str(token["name"])
            converter = token.get("converter")
            if name in param_names:
                return None
            param_names.append(name)
            if isinstance(converter, str) and converter in KNOWN_CONVERTERS:
                parts.append(f"(?P<{name}>{KNOWN_CONVERTERS[converter]})")
            else:
                parts.append(f"(?P<{name}>[^/]+)")
        elif token["kind"] == "regex":
            name = str(token["name"])
            regex = str(token["regex"])
            if name in param_names:
                return None
            param_names.append(name)
            parts.append(f"(?P<{name}>{regex})")
        else:
            return None

        index = token_end + 1

    if not param_names:
        return None

    return ("".join(parts), param_names)


def _extract_single_token_content(segment: str) -> str | None:
    if not segment.startswith("["):
        return None
    end = _find_closing_bracket(segment, 0)
    if end is None or end != len(segment) - 1:
        return None
    return segment[1:end]


def _find_closing_bracket(text: str, open_index: int) -> int | None:
    if open_index >= len(text) or text[open_index] != "[":
        return None
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


def _parse_token_content(content: str) -> dict[str, str]:
    if content.startswith("...") and len(content) > 3:
        return {"kind": "catchall", "name": content[3:]}

    separator = ":" if ":" in content else "__" if "__" in content else ""
    if not separator:
        return {"kind": "dynamic", "name": content}

    left, right = content.split(separator, 1)
    if left in KNOWN_CONVERTERS and _is_identifier(right):
        return {"kind": "dynamic", "name": right, "converter": left}
    if _is_identifier(left):
        return {"kind": "regex", "name": left, "regex": right}
    return {"kind": "dynamic", "name": content}


def _is_identifier(value: str) -> bool:
    return bool(re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", value))
