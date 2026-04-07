from __future__ import annotations

from pathlib import Path

from hyperdjango.conf import get_frontend_dir
from hyperdjango.routing.compiler import build_urlpatterns


def include_routes(base_dir: Path | None = None, url_prefix: str = "") -> list:
    frontend_dir = get_frontend_dir()
    routes_dir = base_dir or (frontend_dir / "routes")
    return build_urlpatterns(routes_dir=routes_dir, url_prefix=url_prefix)
