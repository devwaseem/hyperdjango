from __future__ import annotations

from hyper.layouts.base import BaseLayout


class PageView(BaseLayout):
    def get(self, request, kind: str, version: str, **params):
        return {
            "title": "Composite Regex Segment",
            "kind": kind,
            "version": version,
        }
