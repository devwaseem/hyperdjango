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


def test_parse_typed_dynamic_segment() -> None:
    segment = parse_segment("[str:slug]")
    assert segment.kind == "dynamic"
    assert segment.path_part == "<str:slug>"


def test_parse_typed_dynamic_segment_portable_separator() -> None:
    segment = parse_segment("[str__slug]")
    assert segment.kind == "dynamic"
    assert segment.path_part == "<str:slug>"


def test_parse_inline_regex_segment() -> None:
    segment = parse_segment("[uidb36:[0-9A-Za-z]+]-[key:.+]")
    assert segment.kind == "pattern"
    assert segment.param_names == ("uidb36", "key")
    assert segment.regex_part is not None


def test_parse_inline_regex_segment_portable_separator() -> None:
    segment = parse_segment("[uidb36__[0-9A-Za-z]+]-[key__.+]")
    assert segment.kind == "pattern"
    assert segment.param_names == ("uidb36", "key")


def test_build_regex_route_for_typed_and_inline_regex() -> None:
    segments = [
        parse_segment("reset"),
        parse_segment("[str:slug]"),
        parse_segment("[uid:[0-9]+]-[key:.+]"),
    ]
    regex = build_regex_route(segments)
    assert regex == "^reset/(?P<slug>[^/]+)/(?P<uid>[0-9]+)\\-(?P<key>.+)$"
