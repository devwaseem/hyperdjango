from __future__ import annotations

from django.http import Http404, HttpRequest

from hyper.layouts.docs import DocsLayout
from hyper.shared.docs_content import get_doc_page, get_docs_navigation, render_doc


class PageView(DocsLayout):
    def get(self, request: HttpRequest, slug: str) -> dict[str, object]:
        normalized = slug.strip("/")
        page = get_doc_page(normalized)
        if page is None or page.slug == "":
            raise Http404()

        doc = render_doc(normalized)
        return {
            "title": f"{doc.title} | HyperDjango Docs",
            "doc": doc,
            "current_slug": normalized,
            "docs_navigation": get_docs_navigation(),
            "docs_page": page,
            "is_overview": False,
            "show_group_cards": normalized == "examples",
        }
