from __future__ import annotations

from django.http import HttpRequest


ACTION_HEADER = "HTTP_X_HYPER_ACTION"
TARGET_HEADER = "HTTP_X_HYPER_TARGET"
DATA_HEADER = "HTTP_X_HYPER_DATA"
ACTION_QUERY_KEY = "_action"


def get_action_name(request: HttpRequest) -> str:
    return str(
        request.META.get(ACTION_HEADER, "")
        or request.GET.get(ACTION_QUERY_KEY, "")
        or request.POST.get(ACTION_QUERY_KEY, "")
    ).strip()


def get_target_name(request: HttpRequest) -> str:
    return str(request.META.get(TARGET_HEADER, "")).strip()


def is_action_request(request: HttpRequest) -> bool:
    return bool(get_action_name(request))
