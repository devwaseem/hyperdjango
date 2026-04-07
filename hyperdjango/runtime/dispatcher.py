from __future__ import annotations

import json
from typing import Any

from django.http import HttpRequest, HttpResponse

from hyperdjango.actions import ActionResult
from hyperdjango.runtime.requests import (
    get_action_name,
    get_target_name,
    is_action_request,
)
from hyperdjango.runtime.responses import (
    ensure_action_response_headers,
    to_action_http_response,
)


class DispatchError(Exception):
    pass


def dispatch_page(page: Any, request: HttpRequest, **params: Any) -> HttpResponse:
    if is_action_request(request):
        action_name = get_action_name(request)
        return _dispatch_action(page, request, action_name=action_name, **params)

    handler_name = request.method.lower()
    if not hasattr(page, handler_name):
        raise DispatchError(
            f"Method {request.method} not allowed for page {page.__class__.__name__}"
        )
    handler = getattr(page, handler_name)
    result = handler(request, **params)
    return _to_full_response(page, request, result)


def _dispatch_action(
    page: Any, request: HttpRequest, action_name: str, **params: Any
) -> HttpResponse:
    action_method = page.get_action(action_name)
    if action_method is None:
        raise DispatchError(
            f"Action '{action_name}' not found on page {page.__class__.__name__}"
        )

    action_kwargs = {**_extract_action_kwargs(request), **params}
    result = action_method(request, **action_kwargs)

    if isinstance(result, HttpResponse):
        return ensure_action_response_headers(result)
    if isinstance(result, ActionResult):
        return to_action_http_response(result)
    if isinstance(result, str):
        return ensure_action_response_headers(HttpResponse(result))
    if isinstance(result, dict):
        block_name = get_target_name(request) or action_name
        html = page.render_block(
            request=request,
            block_name=block_name,
            context_updates=result,
        )
        return ensure_action_response_headers(HttpResponse(html))

    raise DispatchError(f"Unsupported action return type: {type(result).__name__}")


def _extract_action_kwargs(request: HttpRequest) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}

    raw_kwargs = request.META.get("HTTP_X_HYPER_SIGNALS", "")
    if raw_kwargs:
        try:
            payload = json.loads(raw_kwargs)
            if isinstance(payload, dict):
                kwargs.update(payload)
        except json.JSONDecodeError:
            pass

    for key, values in request.GET.lists():
        if key == "_action":
            continue
        if key not in kwargs:
            kwargs[key] = values[-1] if values else ""

    if request.method.upper() != "GET":
        for key, values in request.POST.lists():
            if key == "_action":
                continue
            if key not in kwargs:
                kwargs[key] = values[-1] if values else ""

    return kwargs


def _to_full_response(page: Any, request: HttpRequest, result: Any) -> HttpResponse:
    if isinstance(result, HttpResponse):
        return result
    if isinstance(result, str):
        return HttpResponse(result)
    if isinstance(result, dict):
        html = page.render(request=request, context_updates=result)
        return HttpResponse(html)
    raise DispatchError(
        f"Unsupported page handler return type: {type(result).__name__}"
    )
