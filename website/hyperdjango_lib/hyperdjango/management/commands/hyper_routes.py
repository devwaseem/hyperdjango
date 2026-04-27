from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand

from hyperdjango.conf import get_frontend_dir
from hyperdjango.routing.compiler import compile_routes


class Command(BaseCommand):
    help = "Print compiled HyperDjango file routes"

    def add_arguments(self, parser):
        parser.add_argument("--prefix", default="", help="URL prefix")
        parser.add_argument("--dir", default="", help="Override routes directory")
        parser.add_argument(
            "--json", action="store_true", help="Print route map as JSON"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        frontend_dir = get_frontend_dir()
        routes_dir = Path(options["dir"]) if options["dir"] else frontend_dir / "routes"
        compiled = compile_routes(routes_dir=routes_dir, url_prefix=options["prefix"])
        if not compiled:
            self.stdout.write("No routes found.")
            return

        if options["json"]:
            payload = [
                {
                    "path": route.django_path or "/",
                    "page": route.page_class.__name__,
                    "view_name": route.view_name,
                }
                for route in compiled
            ]
            self.stdout.write(json.dumps(payload, indent=2))
            return

        for route in compiled:
            route_path = route.django_path or "/"
            self.stdout.write(f"{route_path} -> {route.page_class.__name__}")
