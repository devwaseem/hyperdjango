from __future__ import annotations

from django.http import HttpRequest

from hyper.layouts.docs import DocsLayout
from hyper.shared.docs_content import get_doc_page, get_docs_navigation, render_doc


class PageView(DocsLayout):
    def get(self, request: HttpRequest) -> dict[str, object]:
        page = get_doc_page("")
        if page is None:
            raise RuntimeError("Docs overview page is not configured")
        doc = render_doc("")
        return {
            "title": f"{doc.title} | HyperDjango Docs",
            "doc": doc,
            "current_slug": "",
            "docs_navigation": get_docs_navigation(),
            "docs_page": page,
            "is_overview": True,
        }
