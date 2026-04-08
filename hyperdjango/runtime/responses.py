from __future__ import annotations

from typing import Any

from django.http import HttpResponse, JsonResponse
from django.utils.cache import patch_vary_headers

from hyperdjango.actions import ActionResult


ACTION_VARY_HEADERS = [
    "X-Hyper-Action",
    "X-Hyper-Target",
    "X-Hyper-Signals",
    "X-Requested-With",
]


def ensure_action_response_headers(response: HttpResponse) -> HttpResponse:
    patch_vary_headers(response, ACTION_VARY_HEADERS)
    response["Cache-Control"] = "no-store, no-cache, max-age=0, must-revalidate"
    response["Pragma"] = "no-cache"
    return response


def to_action_http_response(result: ActionResult) -> HttpResponse:
    should_return_json = bool(
        result.signals
        or result.toasts
        or result.redirect_to
        or result.target
        or result.swap
        or result.swap_delay is not None
        or result.settle_delay is not None
        or result.transition
        or result.focus
        or result.push_url
        or result.replace_url
        or result.strict_targets is not None
        or result.oob
    )

    if should_return_json:
        payload: dict[str, Any] = {}
        if result.signals:
            payload["signals"] = result.signals
        if result.toasts:
            payload["toasts"] = result.toasts
        if result.redirect_to:
            payload["redirect_to"] = result.redirect_to
        if result.html is not None:
            payload["html"] = result.html
        if result.target:
            payload["target"] = result.target
        if result.swap:
            payload["swap"] = result.swap
        if result.swap_delay is not None:
            payload["swap_delay"] = result.swap_delay
        if result.settle_delay is not None:
            payload["settle_delay"] = result.settle_delay
        if result.transition:
            payload["transition"] = result.transition
        if result.focus:
            payload["focus"] = result.focus
        if result.push_url:
            payload["push_url"] = result.push_url
        if result.replace_url:
            payload["replace_url"] = result.replace_url
        if result.strict_targets is not None:
            payload["strict_targets"] = result.strict_targets
        if result.oob:
            payload["oob"] = result.oob
        response = JsonResponse(payload, status=result.status)
    else:
        response = HttpResponse(result.html or "", status=result.status)

    for key, value in result.headers.items():
        response[key] = value
    return ensure_action_response_headers(response)
