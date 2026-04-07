from hyperdjango.routing.parser import (
    build_django_route,
    build_regex_route,
    parse_segment,
)


def test_parse_dynamic_segment() -> None:
    segment = parse_segment("[slug]")
    assert segment.kind == "dynamic"
    assert segment.path_part == "<slug>"


def test_parse_catchall_segment() -> None:
    segment = parse_segment("[...path]")
    assert segment.kind == "catchall"
    assert segment.path_part == "<path:path>"


def test_parse_group_segment() -> None:
    segment = parse_segment("(marketing)")
    assert segment.kind == "group"
    assert segment.path_part == ""


def test_route_build_ignores_index_and_groups() -> None:
    segments = [
        parse_segment("(marketing)"),
        parse_segment("index"),
        parse_segment("pricing"),
    ]
    assert build_django_route(segments) == "pricing"


def test_parse_pattern_segment() -> None:
    segment = parse_segment("[uidb36]-[key]")
    assert segment.kind == "pattern"
    assert segment.regex_part is not None


def test_build_regex_route_for_pattern_segment() -> None:
    segments = [parse_segment("accounts"), parse_segment("[uidb36]-[key]")]
    regex = build_regex_route(segments)
    assert regex == "^accounts/(?P<uidb36>[^/]+)\\-(?P<key>[^/]+)$"
