from __future__ import annotations

from typing import Any

from django.http import HttpRequest, HttpResponse

from hyperdjango.page import PageTemplate


def render_template_page(
    request: HttpRequest,
    template_cls: type[PageTemplate],
    *,
    context: dict[str, Any] | None = None,
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> HttpResponse:
    page = template_cls()
    html = page.render(request=request, context_updates=context)
    response = HttpResponse(html, status=status)
    for key, value in (headers or {}).items():
        response[key] = value
    return response


def render_template_block(
    request: HttpRequest,
    template_cls: type[PageTemplate],
    block_name: str,
    *,
    context: dict[str, Any] | None = None,
    relative_template_name: str = "",
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> HttpResponse:
    page = template_cls()
    html = page.render_block(
        request=request,
        block_name=block_name,
        relative_template_name=relative_template_name,
        context_updates=context,
    )
    response = HttpResponse(html, status=status)
    for key, value in (headers or {}).items():
        response[key] = value
    return response
