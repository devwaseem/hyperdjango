from __future__ import annotations

from hyper.layouts.base import BaseLayout


class PageView(BaseLayout):
    def get(self, request, uidb36: str, key: str, **params):
        return {
            "title": "Inline Regex Segment",
            "uidb36": uidb36,
            "key": key,
        }
