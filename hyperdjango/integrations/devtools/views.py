from __future__ import annotations

import json

from django.http import Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from hyperdjango.integrations.debug_toolbar.tracing import (
    sanitize_mapping,
    sanitize_value,
)
from hyperdjango.integrations.devtools import is_enabled
from hyperdjango.integrations.devtools.store import request_store

DOM_DIFF_FIELDS = ("added_nodes", "removed_nodes", "changed_nodes")


def _require_enabled() -> None:
    if not is_enabled():
        raise Http404


@never_cache
@require_GET
def history(request):
    _require_enabled()
    return JsonResponse(
        {"records": request_store.history(), "paused": request_store.paused}
    )


@never_cache
@require_GET
def detail(request, request_id: str):
    _require_enabled()
    record = request_store.get(request_id)
    if record is None:
        raise Http404
    return JsonResponse({"record": record})


def _json_body(request) -> dict:
    try:
        value = json.loads(request.body or b"{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _sanitize_client_event(value: dict) -> dict:
    sanitized = sanitize_mapping(value)
    for field in DOM_DIFF_FIELDS:
        items = value.get(field)
        if isinstance(items, list):
            # The collector already bounds each category to 30 nodes. Preserve the
            # complete descriptions so the inspector's scrollable diff is useful.
            sanitized[field] = [str(item) for item in items[:30]]
    return sanitized


@csrf_exempt
@require_POST
def client_update(request, request_id: str):
    _require_enabled()
    payload = _json_body(request)
    client = {
        "events": [
            _sanitize_client_event(item)
            if isinstance(item, dict)
            else sanitize_value(item)
            for item in payload.get("events", [])[:200]
        ],
        "summary": (
            sanitize_mapping(payload["summary"])
            if isinstance(payload.get("summary"), dict)
            else sanitize_value(payload.get("summary", {}))
        ),
    }
    if not request_store.update_client(request_id, client):
        raise Http404
    return JsonResponse({"updated": True})


@csrf_exempt
@require_POST
def pin(request, request_id: str):
    _require_enabled()
    pinned = request_store.toggle_pin(request_id)
    if pinned is None:
        raise Http404
    return JsonResponse({"pinned": pinned})


@csrf_exempt
@require_POST
def clear(request):
    _require_enabled()
    return JsonResponse({"cleared": request_store.clear()})


@csrf_exempt
@require_POST
def pause(request):
    _require_enabled()
    return JsonResponse({"paused": request_store.toggle_pause()})
