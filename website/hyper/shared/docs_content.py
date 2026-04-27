from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from typing import Final

from django.utils.safestring import SafeString, mark_safe
import markdown


REPO_DIR: Final[Path] = Path(__file__).resolve().parents[3]
DOCS_DIR: Final[Path] = REPO_DIR / "docs"


@dataclass(frozen=True, slots=True)
class DocPage:
    slug: str
    source: str
    nav_title: str
    group: str
    summary: str


@dataclass(frozen=True, slots=True)
class RenderedDoc:
    slug: str
    title: str
    summary: str
    html: SafeString
    source_path: Path


DOC_PAGES: Final[tuple[DocPage, ...]] = (
    DocPage(
        slug="",
        source="index.md",
        nav_title="Overview",
        group="Guides",
        summary="Start here for the core ideas, the Django-first mental model, and how the docs are organized.",
    ),
    DocPage(
        slug="getting-started",
        source="installation.md",
        nav_title="Getting Started",
        group="Guides",
        summary="Install HyperDjango, wire Django settings, mount routes, and build the first page and action.",
    ),
    DocPage(
        slug="routing",
        source="routing.md",
        nav_title="Routing",
        group="Guides",
        summary="Learn file-based routing, nested pages, dynamic params, typed params, regex routes, and reverse names.",
    ),
    DocPage(
        slug="pages-and-rendering",
        source="pages-and-rendering.md",
        nav_title="Pages and Rendering",
        group="Guides",
        summary="Understand HyperView, plain Django View, render helpers, template packages, and standalone template rendering.",
    ),
    DocPage(
        slug="layouts",
        source="layouts.md",
        nav_title="Layouts",
        group="Guides",
        summary="Use reusable layout packages in hyper/layouts to share templates, assets, and server behavior.",
    ),
    DocPage(
        slug="base-template",
        source="base-template.md",
        nav_title="Base Template",
        group="Guides",
        summary="Understand the shipped hyperdjango/base.html template, what it includes by default, and how to replace it safely.",
    ),
    DocPage(
        slug="actions",
        source="actions.md",
        nav_title="Actions",
        group="Guides",
        summary="Write HyperDjango actions, return typed response items, and understand immediate versus streaming responses.",
    ),
    DocPage(
        slug="client-side-actions",
        source="client-side-actions.md",
        nav_title="Client-Side Actions",
        group="Guides",
        summary="Invoke actions from Alpine or plain JavaScript and understand sync, key, upload progress, and runtime events.",
    ),
    DocPage(
        slug="declarative-html-apis",
        source="declarative-html-apis.md",
        nav_title="Declarative HTML APIs",
        group="Guides",
        summary="Use hyper-form-disable, hyper-loading, and hyper-view-transition-name when declarative HTML is clearer than inline JavaScript.",
    ),
    DocPage(
        slug="alpine-integration",
        source="alpine-integration.md",
        nav_title="Alpine Integration",
        group="Guides",
        summary="Learn how HyperDjango integrates with Alpine through $action, local signal patches, and the global $store.hyper bridge.",
    ),
    DocPage(
        slug="assets-and-vite",
        source="assets-and-vite.md",
        nav_title="Assets and Vite",
        group="Guides",
        summary="Understand automatic entry discovery, Vite development and production asset loading, and template asset tags.",
    ),
    DocPage(
        slug="reference",
        source="reference/index.md",
        nav_title="Overview",
        group="Reference",
        summary="Start here for the API-style reference pages.",
    ),
    DocPage(
        slug="reference/django-integration",
        source="reference/django-integration.md",
        nav_title="Django Integration",
        group="Reference",
        summary="Exact reference for include_routes and Django URL wiring.",
    ),
    DocPage(
        slug="reference/settings",
        source="reference/settings.md",
        nav_title="Settings",
        group="Reference",
        summary="Exact reference for HYPER_FRONTEND_DIR, HYPER_VITE_OUTPUT_DIR, HYPER_VITE_DEV_SERVER_URL, and HYPER_DEV.",
    ),
    DocPage(
        slug="reference/pages-and-rendering",
        source="reference/pages-and-rendering.md",
        nav_title="Pages and Rendering",
        group="Reference",
        summary="Method signatures and return details for HyperView, HyperPageTemplate, and rendering shortcuts.",
    ),
    DocPage(
        slug="reference/actions",
        source="reference/actions.md",
        nav_title="Actions",
        group="Reference",
        summary="Detailed arguments and supported return shapes for action items and action methods.",
    ),
    DocPage(
        slug="reference/client-runtime",
        source="reference/client-runtime.md",
        nav_title="Client Runtime",
        group="Reference",
        summary="Detailed reference for $action, window.action, runtime outcomes, and browser events.",
    ),
    DocPage(
        slug="reference/html-apis",
        source="reference/html-apis.md",
        nav_title="HTML APIs",
        group="Reference",
        summary="Reference for hyper-form-disable, hyper-view-transition-name, and loading-related attributes.",
    ),
    DocPage(
        slug="reference/template-tags",
        source="reference/template-tags.md",
        nav_title="Template Tags",
        group="Reference",
        summary="Reference for hyper_preloads, hyper_stylesheets, hyper_head_scripts, hyper_body_scripts, and hyper_custom_entry.",
    ),
    DocPage(
        slug="reference/commands",
        source="reference/commands.md",
        nav_title="Commands",
        group="Reference",
        summary="Reference for hyper_scaffold and hyper_routes.",
    ),
    DocPage(
        slug="troubleshooting",
        source="troubleshooting.md",
        nav_title="Troubleshooting",
        group="Guides",
        summary="Debug common issues such as missing targets, CSRF failures, route conflicts, and view transition expectations.",
    ),
    DocPage(
        slug="production-checklist",
        source="production-checklist.md",
        nav_title="Production Checklist",
        group="Guides",
        summary="Validate production settings, caching, static assets, and request behavior before shipping HyperDjango pages.",
    ),
    DocPage(
        slug="faq",
        source="faq.md",
        nav_title="FAQ",
        group="Guides",
        summary="Quick answers for View vs HyperView, layout choices, render helpers, Alpine, and action return patterns.",
    ),
)


TOCTREE_PATTERN: Final[re.Pattern[str]] = re.compile(r"```\{toctree\}.*?```", re.DOTALL)


def get_doc_page(slug: str) -> DocPage | None:
    normalized = slug.strip("/")
    for page in DOC_PAGES:
        if page.slug == normalized:
            return page
    return None


def get_docs_navigation() -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for page in DOC_PAGES:
        grouped.setdefault(page.group, []).append(
            {
                "slug": page.slug,
                "href": f"/docs/{page.slug}" if page.slug else "/docs",
                "title": page.nav_title,
                "summary": page.summary,
            }
        )
    return [{"title": title, "pages": pages} for title, pages in grouped.items()]


@lru_cache(maxsize=None)
def render_doc(slug: str) -> RenderedDoc:
    page = get_doc_page(slug)
    if page is None:
        raise FileNotFoundError(slug)
    source_path = DOCS_DIR / page.source
    raw = source_path.read_text(encoding="utf-8")
    cleaned = TOCTREE_PATTERN.sub("", raw).strip()
    title, body = _split_title(cleaned)
    html = markdown.markdown(
        body,
        extensions=[
            "fenced_code",
            "tables",
            "sane_lists",
            "toc",
        ],
        output_format="html5",
    )
    return RenderedDoc(
        slug=page.slug,
        title=title,
        summary=page.summary,
        html=mark_safe(html),
        source_path=source_path,
    )


def _split_title(content: str) -> tuple[str, str]:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            body = "\n".join(lines[index + 1 :]).strip()
            return title, body
    return "HyperDjango Docs", content
