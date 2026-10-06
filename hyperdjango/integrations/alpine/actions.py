from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Signal:
    name: str
    value: Any
    only_if_missing: bool = False


@dataclass(slots=True)
class Signals:
    values: dict[str, Any]
    only_if_missing: bool = False
