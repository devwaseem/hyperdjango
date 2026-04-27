from __future__ import annotations

import json
from typing import Any, Final

from django.conf import settings


SITE_NAME: Final[str] = "HyperDjango"


def site_url() -> str:
    return str(
        getattr(
            settings, "SITE_URL", "https://hyperdjango.charingcrosscapital.com"
        )
    ).rstrip("/")


def absolute_url(path: str = "/") -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{site_url()}{normalized}"


def seo_context(
    *,
    title: str,
    description: str,
    path: str,
    json_ld: Any | None = None,
    robots: str = "index,follow",
) -> dict[str, Any]:
    return {
        "title": title,
        "meta_description": description,
        "canonical_url": absolute_url(path),
        "meta_robots": robots,
        "json_ld": json.dumps(json_ld, ensure_ascii=False)
        if json_ld is not None
        else "",
        "site_name": SITE_NAME,
        "site_url": site_url(),
    }


def site_json_ld() -> list[dict[str, Any]]:
    base = site_url()
    return [
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": SITE_NAME,
            "url": base,
        },
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": SITE_NAME,
            "url": base,
            "publisher": {"@type": "Organization", "name": SITE_NAME},
        },
        {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": SITE_NAME,
            "applicationCategory": "DeveloperApplication",
            "operatingSystem": "Web",
            "url": base,
        },
    ]


def page_json_ld(*, title: str, description: str, path: str) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": description,
        "url": absolute_url(path),
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": site_url()},
    }
