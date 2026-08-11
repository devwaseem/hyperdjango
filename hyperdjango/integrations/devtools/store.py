from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from threading import RLock
from typing import Any

from django.conf import settings


def _history_limit() -> int:
    config = getattr(settings, "HYPER_DEBUG_TOOLBAR_CONFIG", {})
    try:
        return max(5, min(int(config.get("MAX_HISTORY", 50)), 500))
    except (TypeError, ValueError):
        return 50


class RequestStore:
    def __init__(self) -> None:
        self._records: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = RLock()
        self._pinned: set[str] = set()
        self._paused = False

    @property
    def paused(self) -> bool:
        with self._lock:
            return self._paused

    def save(self, request_id: str, record: dict[str, Any]) -> None:
        with self._lock:
            self._records[request_id] = deepcopy(record)
            self._records.move_to_end(request_id)
            while len(self._records) > _history_limit():
                removable = next(
                    (key for key in self._records if key not in self._pinned), None
                )
                if removable is None:
                    break
                del self._records[removable]

    def get(self, request_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._records.get(request_id)
            return deepcopy(record) if record is not None else None

    def history(self) -> list[dict[str, Any]]:
        with self._lock:
            records = list(reversed(self._records.items()))
            pinned = set(self._pinned)
        return [
            {**self._summary(request_id, record), "pinned": request_id in pinned}
            for request_id, record in records
        ]

    def update_client(self, request_id: str, client: dict[str, Any]) -> bool:
        with self._lock:
            record = self._records.get(request_id)
            if record is None:
                return False
            record["client"] = deepcopy(client)
            self._records.move_to_end(request_id)
            return True

    def toggle_pin(self, request_id: str) -> bool | None:
        with self._lock:
            if request_id not in self._records:
                return None
            if request_id in self._pinned:
                self._pinned.remove(request_id)
                return False
            self._pinned.add(request_id)
            return True

    def clear(self) -> int:
        with self._lock:
            removable = [key for key in self._records if key not in self._pinned]
            for key in removable:
                del self._records[key]
            return len(removable)

    def toggle_pause(self) -> bool:
        with self._lock:
            self._paused = not self._paused
            return self._paused

    @staticmethod
    def _summary(request_id: str, record: dict[str, Any]) -> dict[str, Any]:
        request = record.get("request", {})
        response = record.get("response", {})
        route = record.get("route", {})
        action = record.get("action", {})
        results = record.get("results", [])
        return {
            "id": request_id,
            "method": request.get("method"),
            "path": request.get("path"),
            "started_at": request.get("started_at"),
            "status": response.get("status"),
            "duration_ms": response.get("request_duration_ms"),
            "handler": route.get("handler"),
            "action": action.get("name"),
            "streaming": bool(response.get("streaming")),
            "stream_status": response.get("stream_status")
            or next(
                (
                    result.get("iteration_status")
                    for result in reversed(results)
                    if result.get("streaming")
                ),
                None,
            ),
            "exceptions": len(record.get("exceptions", [])),
        }


request_store = RequestStore()
