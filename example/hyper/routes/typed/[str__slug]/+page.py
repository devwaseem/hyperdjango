from __future__ import annotations

from hyper.layouts.base import BaseLayout


class PageView(BaseLayout):
    def get(self, request, slug: str, **params):
        return {
            "title": "Typed Dynamic Segment",
            "slug": slug,
        }
