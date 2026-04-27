from __future__ import annotations

from django.http import HttpRequest

from hyper.layouts.docs import DocsLayout
from hyper.shared.docs_content import (
    get_doc_page,
    get_docs_navigation,
    get_related_doc_pages,
    render_doc,
)
from hyper.shared.seo import breadcrumb_json_ld, page_json_ld, seo_context


class PageView(DocsLayout):
    def get(self, request: HttpRequest) -> dict[str, object]:
        page = get_doc_page("")
        if page is None:
            raise RuntimeError("Docs overview page is not configured")
        doc = render_doc("")
        return {
            **seo_context(
                title="Docs | HyperDjango",
                description=doc.summary,
                path="/docs",
                json_ld=page_json_ld(
                    title="Docs | HyperDjango",
                    description=doc.summary,
                    path="/docs",
                ),
            ),
            "doc": doc,
            "current_slug": "",
            "docs_navigation": get_docs_navigation(),
            "docs_page": page,
            "is_overview": True,
            "page_lede": "Start with Getting Started, then move through routing, rendering, and the reference pages once the core concepts are clear.",
            "previous_doc": None,
            "next_doc": None,
            "related_docs": get_related_doc_pages(""),
            "previous_url": None,
            "next_url": None,
            "breadcrumb_json_ld": breadcrumb_json_ld(
                [("Home", "/"), ("Docs", "/docs")]
            ),
        }
