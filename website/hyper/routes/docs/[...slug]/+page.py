from __future__ import annotations

from django.http import Http404, HttpRequest

from hyper.layouts.docs import DocsLayout
from hyper.shared.docs_content import (
    get_adjacent_doc_pages,
    get_doc_page,
    get_docs_navigation,
    get_related_doc_pages,
    render_doc,
)
from hyper.shared.seo import breadcrumb_json_ld, page_json_ld, seo_context


class PageView(DocsLayout):
    def get(self, request: HttpRequest, slug: str) -> dict[str, object]:
        normalized = slug.strip("/")
        page = get_doc_page(normalized)
        if page is None or page.slug == "":
            raise Http404()

        doc = render_doc(normalized)
        previous_doc, next_doc = get_adjacent_doc_pages(normalized)
        return {
            **seo_context(
                title=f"{doc.title} | HyperDjango",
                description=doc.summary,
                path=f"/docs/{normalized}",
                json_ld=page_json_ld(
                    title=f"{doc.title} | HyperDjango",
                    description=doc.summary,
                    path=f"/docs/{normalized}",
                ),
            ),
            "doc": doc,
            "current_slug": normalized,
            "docs_navigation": get_docs_navigation(),
            "docs_page": page,
            "is_overview": False,
            "show_group_cards": normalized == "examples",
            "page_lede": "This page focuses on the practical details. Use the quick links below to move to the previous, next, or related docs.",
            "previous_doc": previous_doc,
            "next_doc": next_doc,
            "related_docs": get_related_doc_pages(normalized),
            "previous_url": previous_doc.href if previous_doc else None,
            "next_url": next_doc.href if next_doc else None,
            "breadcrumb_json_ld": breadcrumb_json_ld(
                [
                    ("Home", "/"),
                    ("Docs", "/docs"),
                    (doc.title, f"/docs/{normalized}"),
                ]
            ),
        }
