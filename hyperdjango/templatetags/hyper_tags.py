from __future__ import annotations

from typing import cast

from django import template
from django.utils.safestring import mark_safe

from hyperdjango.assets import AssetTag
from hyperdjango.page import Page


register = template.Library()


class PageContextNotFoundError(Exception):
    pass


def _get_page(context: template.Context) -> Page:
    if "page" not in context:
        raise PageContextNotFoundError("Page not found in template context")
    return cast(Page, context["page"])


def _render_tags(tags: list[AssetTag], nonce: str | None = None) -> str:
    return mark_safe("\n".join(tag.render(nonce=nonce) for tag in tags))


def _get_csp_nonce(context: template.Context) -> str | None:
    request = context.get("request")
    if not request:
        return None
    return cast(str | None, getattr(request, "_csp_nonce", None))


@register.simple_tag(takes_context=True)
def hyper_preloads(context: template.Context) -> str:
    page = _get_page(context)
    return _render_tags(cast(list[AssetTag], page.preload_imports))


@register.simple_tag(takes_context=True)
def hyper_stylesheets(context: template.Context) -> str:
    page = _get_page(context)
    return _render_tags(
        cast(list[AssetTag], page.stylesheets), nonce=_get_csp_nonce(context)
    )


@register.simple_tag(takes_context=True)
def hyper_head_scripts(context: template.Context) -> str:
    page = _get_page(context)
    return _render_tags(
        cast(list[AssetTag], page.head_imports), nonce=_get_csp_nonce(context)
    )


@register.simple_tag(takes_context=True)
def hyper_body_scripts(context: template.Context) -> str:
    page = _get_page(context)
    return _render_tags(
        cast(list[AssetTag], page.body_imports), nonce=_get_csp_nonce(context)
    )


@register.simple_tag(takes_context=True)
def hyper_custom_entry(context: template.Context, name: str) -> str:
    page = _get_page(context)
    files = [f"{name}.entry.js", f"{name}.entry.ts"]
    tags: list[AssetTag] = []
    for file_name in files:
        try:
            tags.extend(list(page.resolve_import(file_name=file_name)))
        except FileNotFoundError:
            continue
    if not tags:
        raise FileNotFoundError(
            f"Could not find custom entry '{name}'. Tried: {', '.join(files)}"
        )
    return _render_tags(tags, nonce=_get_csp_nonce(context))
