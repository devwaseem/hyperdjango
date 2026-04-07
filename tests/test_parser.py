from hyperdjango.routing.parser import build_django_route, parse_segment


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
