from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from django.http import HttpRequest


_VALID_SSE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_VALID_CHECKPOINT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_CHECKPOINT_MARKER = ":checkpoint:"


@dataclass(frozen=True, slots=True)
class ResumeCheckpoint:
    """A named SSE checkpoint acknowledged by the client."""

    name: str
    index: int


def validate_checkpoint_name(name: str) -> str:
    if not isinstance(name, str) or not _VALID_CHECKPOINT_NAME.fullmatch(name):
        raise ValueError(
            "checkpoint name must match "
            "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
        )
    return name


def is_valid_sse_request_id(request_id: str) -> bool:
    return bool(_VALID_SSE_REQUEST_ID.fullmatch(request_id))


def format_checkpoint_event_id(request_id: str, checkpoint: str) -> str:
    if not is_valid_sse_request_id(request_id):
        raise ValueError("checkpoint requires a valid X-Hyper-Request-ID")
    return f"{request_id}{_CHECKPOINT_MARKER}{validate_checkpoint_name(checkpoint)}"


def get_resume_checkpoint(
    request: HttpRequest,
    *,
    allowed: Sequence[str],
) -> ResumeCheckpoint | None:
    """Return the last acknowledged checkpoint for a retryable GET action.

    Incoming cursor headers are untrusted. Malformed, stale, cross-request, and
    non-GET cursors restart from the beginning by returning ``None``.
    """

    if isinstance(allowed, (str, bytes)):
        raise ValueError("allowed must be an ordered sequence of checkpoint names")
    checkpoints = tuple(validate_checkpoint_name(name) for name in allowed)
    if len(set(checkpoints)) != len(checkpoints):
        raise ValueError("checkpoint names in allowed must be unique")

    method = request.method if isinstance(request.method, str) else "GET"
    if method.upper() != "GET":
        return None

    request_id = request.headers.get("X-Hyper-Request-ID", "").strip()
    if not is_valid_sse_request_id(request_id):
        return None

    last_event_id = request.headers.get("Last-Event-ID", "").strip()
    prefix = f"{request_id}{_CHECKPOINT_MARKER}"
    if not last_event_id.startswith(prefix):
        return None

    name = last_event_id[len(prefix) :]
    if not _VALID_CHECKPOINT_NAME.fullmatch(name):
        return None
    try:
        index = checkpoints.index(name)
    except ValueError:
        return None
    return ResumeCheckpoint(name=name, index=index)
