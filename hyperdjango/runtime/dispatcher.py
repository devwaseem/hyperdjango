from __future__ import annotations

import inspect
import json
import logging
from collections.abc import Iterable
from typing import Any

from asgiref.sync import async_to_sync
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.http import Http404

from hyperdjango.actions import ActionResult
from hyperdjango.integrations.debug_toolbar.tracing import (
    operation as debug_operation,
    record_action as debug_record_action,
    record_dispatch as debug_record_dispatch,
    record_exception as debug_record_exception,
    record_render as debug_record_render,
    record_result as debug_record_result,
)
from hyperdjango.runtime.requests import (
    DATA_HEADER,
    get_action_name,
    get_target_name,
    is_action_request,
)
from hyperdjango.runtime.responses import (
    ensure_action_response_headers,
    is_action_item,
    is_action_item_async_iterable,
    is_action_item_iterable,
    to_action_exception_response,
    to_action_http_response,
)


class DispatchError(Exception):
    pass


_NO_PAGE_RESULT = object()
logger = logging.getLogger("django.request")


def dispatch_page(page: Any, request: HttpRequest, **params: Any) -> HttpResponse:
    return dispatch_page_sync(page, request, **params)


def dispatch_page_sync(page: Any, request: HttpRequest, **params: Any) -> HttpResponse:
    action_name = get_action_name(request) if is_action_request(request) else ""
    method = request.method if isinstance(request.method, str) else "GET"
    handler_name = f"action:{action_name}" if action_name else method.lower()
    debug_record_dispatch(
        request, page, handler=handler_name, route_params=params
    )
    try:
        with debug_operation(request, "dispatch"):
            return _dispatch_page_sync(page, request, **params)
    except BaseException as exc:
        debug_record_exception(request, exc, phase="dispatch")
        raise


def _dispatch_page_sync(page: Any, request: HttpRequest, **params: Any) -> HttpResponse:
    if is_action_request(request):
        action_name = get_action_name(request)
        return _dispatch_action_sync(page, request, action_name=action_name, **params)

    request_method = request.method
    method = request_method if isinstance(request_method, str) else "GET"
    handler_name = method.lower()
    if not hasattr(page, handler_name):
        if handler_name == "get" and hasattr(page, "get_context"):
            return _to_full_response(page, request, _NO_PAGE_RESULT)
        raise DispatchError(
            f"Method {method} not allowed for page {page.__class__.__name__}"
        )
    handler = getattr(page, handler_name)
    result = handler(request, **params)
    if inspect.isawaitable(result):
        result = async_to_sync(_await_result)(result)
    return _to_full_response(page, request, result)


async def dispatch_page_async(
    page: Any, request: HttpRequest, **params: Any
) -> HttpResponse:
    action_name = get_action_name(request) if is_action_request(request) else ""
    method = request.method if isinstance(request.method, str) else "GET"
    handler_name = f"action:{action_name}" if action_name else method.lower()
    debug_record_dispatch(
        request, page, handler=handler_name, route_params=params
    )
    try:
        with debug_operation(request, "dispatch"):
            return await _dispatch_page_async(page, request, **params)
    except BaseException as exc:
        debug_record_exception(request, exc, phase="dispatch")
        raise


async def _dispatch_page_async(
    page: Any, request: HttpRequest, **params: Any
) -> HttpResponse:
    if is_action_request(request):
        action_name = get_action_name(request)
        return await _dispatch_action_async(
            page, request, action_name=action_name, **params
        )

    request_method = request.method
    method = request_method if isinstance(request_method, str) else "GET"
    handler_name = method.lower()
    if not hasattr(page, handler_name):
        if handler_name == "get" and hasattr(page, "get_context"):
            return _to_full_response(page, request, _NO_PAGE_RESULT)
        raise DispatchError(
            f"Method {method} not allowed for page {page.__class__.__name__}"
        )
    handler = getattr(page, handler_name)
    result = handler(request, **params)
    if inspect.isawaitable(result):
        result = await result
    return _to_full_response(page, request, result)


def _dispatch_action_sync(
    page: Any, request: HttpRequest, action_name: str, **params: Any
) -> HttpResponse:
    action_method = page.get_action(action_name)
    if action_method is None:
        raise DispatchError(
            f"Action '{action_name}' not found on page {page.__class__.__name__}"
        )

    action_kwargs = {**_extract_action_kwargs(request), **params}
    debug_record_action(
        request,
        name=action_name,
        target=get_target_name(request),
        arguments=action_kwargs,
    )
    try:
        with debug_operation(request, "action"):
            result = action_method(request, **action_kwargs)
            if inspect.isawaitable(result):
                result = async_to_sync(_await_result)(result)
    except PermissionDenied as exc:
        debug_record_exception(request, exc, phase="action")
        message = str(exc).strip() or "Forbidden"
        logger.warning(
            "Hyper action '%s' denied on %s: %s",
            action_name,
            request.path,
            message,
            exc_info=True,
        )
        return _prepare_action_exception_response(
            request, status=403, message=message
        )
    except Http404 as exc:
        debug_record_exception(request, exc, phase="action")
        message = str(exc).strip() or "Not found"
        logger.warning(
            "Hyper action '%s' not found on %s: %s",
            action_name,
            request.path,
            message,
            exc_info=True,
        )
        return _prepare_action_exception_response(
            request, status=404, message=message
        )
    except Exception as exc:
        debug_record_exception(request, exc, phase="action")
        logger.exception(
            "Unhandled exception in hyper action '%s' on %s",
            action_name,
            request.path,
        )
        return _prepare_action_exception_response(
            request, status=500, message="Internal server error"
        )

    return _dispatch_action_result(page, request, action_name, result)


async def _dispatch_action_async(
    page: Any, request: HttpRequest, action_name: str, **params: Any
) -> HttpResponse:
    action_method = page.get_action(action_name)
    if action_method is None:
        raise DispatchError(
            f"Action '{action_name}' not found on page {page.__class__.__name__}"
        )

    action_kwargs = {**_extract_action_kwargs(request), **params}
    debug_record_action(
        request,
        name=action_name,
        target=get_target_name(request),
        arguments=action_kwargs,
    )
    try:
        with debug_operation(request, "action"):
            result = action_method(request, **action_kwargs)
            if inspect.isawaitable(result):
                result = await result
    except PermissionDenied as exc:
        debug_record_exception(request, exc, phase="action")
        message = str(exc).strip() or "Forbidden"
        logger.warning(
            "Hyper action '%s' denied on %s: %s",
            action_name,
            request.path,
            message,
            exc_info=True,
        )
        return _prepare_action_exception_response(
            request, status=403, message=message
        )
    except Http404 as exc:
        debug_record_exception(request, exc, phase="action")
        message = str(exc).strip() or "Not found"
        logger.warning(
            "Hyper action '%s' not found on %s: %s",
            action_name,
            request.path,
            message,
            exc_info=True,
        )
        return _prepare_action_exception_response(
            request, status=404, message=message
        )
    except Exception as exc:
        debug_record_exception(request, exc, phase="action")
        logger.exception(
            "Unhandled exception in hyper action '%s' on %s",
            action_name,
            request.path,
        )
        return _prepare_action_exception_response(
            request, status=500, message="Internal server error"
        )

    return _dispatch_action_result(page, request, action_name, result)


def _prepare_action_exception_response(
    request: HttpRequest, *, status: int, message: str
) -> HttpResponse:
    with debug_operation(request, "response preparation"):
        return to_action_exception_response(
            status=status, message=message, request=request
        )


def _dispatch_action_result(
    page: Any, request: HttpRequest, action_name: str, result: Any
) -> HttpResponse:
    debug_record_result(request, result)
    with debug_operation(request, "response preparation"):
        if isinstance(result, HttpResponse):
            return ensure_action_response_headers(result)
        if isinstance(result, ActionResult):
            return to_action_http_response(result, request=request)
        if isinstance(result, str):
            return to_action_http_response(ActionResult(html=result), request=request)
        if isinstance(result, dict):
            block_name = get_target_name(request) or action_name
            html = page.render_block(
                request=request,
                block_name=block_name,
                context_updates=result,
            )
            return to_action_http_response(ActionResult(html=html), request=request)
        if (
            is_action_item(result)
            or is_action_item_iterable(result)
            or is_action_item_async_iterable(result)
        ):
            return to_action_http_response(result, request=request)

    raise DispatchError(f"Unsupported action return type: {type(result).__name__}")


def _extract_action_kwargs(request: HttpRequest) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}

    raw_kwargs = request.META.get(DATA_HEADER, "")
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

    request_method = request.method
    method = request_method if isinstance(request_method, str) else "GET"
    if method.upper() != "GET":
        for key, values in request.POST.lists():
            if key == "_action":
                continue
            if key not in kwargs:
                kwargs[key] = values[-1] if values else ""

    return kwargs


def _to_full_response(page: Any, request: HttpRequest, result: Any) -> HttpResponse:
    with debug_operation(request, "response preparation"):
        if isinstance(result, HttpResponse):
            return result
        if isinstance(result, str):
            return HttpResponse(result.encode())
        if result is _NO_PAGE_RESULT or isinstance(result, dict):
            context_updates = result if isinstance(result, dict) else None
            if hasattr(page, "_build_context") and hasattr(
                page, "_render_template_name"
            ):
                context = page._build_context(request, context_updates)
                template_name = page.get_template_name()
                render_event = debug_record_render(
                    request, kind="full page", template=template_name
                )
                with debug_operation(request, "render", render_event):
                    html = page._render_template_name(
                        template_name,
                        request=request,
                        context=context,
                    )
            else:
                html = page.render(request=request, context_updates=context_updates)
            return HttpResponse(html.encode())
    raise DispatchError(
        f"Unsupported page handler return type: {type(result).__name__}"
    )
