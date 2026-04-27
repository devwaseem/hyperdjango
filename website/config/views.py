from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from hyper.shared.docs_content import (
    get_doc_last_modified,
    get_latest_docs_mtime,
    iter_doc_paths,
)
from hyper.shared.seo import absolute_url, page_json_ld, seo_context


WEBSITE_DIR = Path(__file__).resolve().parents[1]


HOME_SOURCE_FILES = [
    WEBSITE_DIR / "hyper" / "routes" / "index" / "+page.py",
    WEBSITE_DIR / "hyper" / "routes" / "index" / "index.html",
    WEBSITE_DIR / "hyper" / "routes" / "index" / "partials" / "hero.html",
    WEBSITE_DIR / "hyper" / "routes" / "index" / "partials" / "footer.html",
]


def _format_mtime(path: Path) -> str:
    return (
        datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        .date()
        .isoformat()
    )


def robots_txt(_request: HttpRequest) -> HttpResponse:
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            f"Sitemap: {absolute_url('/sitemap.xml')}",
            "",
        ]
    )
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


def sitemap_xml(_request: HttpRequest) -> HttpResponse:
    urls = [
        ("/", max(_format_mtime(path) for path in HOME_SOURCE_FILES)),
        ("/docs", get_doc_last_modified("")),
        *[
            (path, get_doc_last_modified(path.removeprefix("/docs/")))
            for path in iter_doc_paths()
            if path != "/docs"
        ],
        ("/llms.txt", get_latest_docs_mtime()),
    ]
    entries = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path, lastmod in dict.fromkeys(urls):
        entries.append(
            "  <url>"
            f"<loc>{escape(absolute_url(path))}</loc>"
            f"<lastmod>{escape(lastmod)}</lastmod>"
            "</url>"
        )
    entries.append("</urlset>")
    return HttpResponse(
        "\n".join(entries), content_type="application/xml; charset=utf-8"
    )


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    context = {
        **seo_context(
            title="Page Not Found | HyperDjango",
            description="The requested page could not be found.",
            path=request.path,
            json_ld=page_json_ld(
                title="Page Not Found | HyperDjango",
                description="The requested page could not be found.",
                path=request.path,
            ),
            robots="noindex,nofollow",
        ),
        "error_title": "Page Not Found",
        "error_message": "The page you requested does not exist or has moved.",
    }
    response = render(request, "404.html", context=context, status=404)
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


def server_error(request: HttpRequest) -> HttpResponse:
    context = {
        **seo_context(
            title="Server Error | HyperDjango",
            description="An unexpected server error occurred.",
            path=request.path,
            json_ld=page_json_ld(
                title="Server Error | HyperDjango",
                description="An unexpected server error occurred.",
                path=request.path,
            ),
            robots="noindex,nofollow",
        ),
        "error_title": "Server Error",
        "error_message": "Something went wrong on the server. Please try again.",
    }
    response = render(request, "500.html", context=context, status=500)
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response
