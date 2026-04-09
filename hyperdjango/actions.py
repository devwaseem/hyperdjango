from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class Signal:
    name: str
    value: Any


@dataclass(slots=True)
class Signals:
    values: dict[str, Any]


@dataclass(slots=True)
class HTML:
    content: str
    target: str | None = None
    swap: str = "inner"
    transition: bool = False
    focus: str | None = None
    swap_delay: int | None = None
    settle_delay: int | None = None
    strict_targets: bool | None = None


@dataclass(slots=True)
class Toast:
    payload: Any


@dataclass(slots=True)
class OOB:
    payload: Any


@dataclass(slots=True)
class Redirect:
    url: str
    replace: bool = False


@dataclass(slots=True)
class History:
    push_url: str | None = None
    replace_url: str | None = None


@dataclass(slots=True)
class LoadJS:
    src: str


ActionItem = Signal | Signals | HTML | Toast | OOB | Redirect | History | LoadJS


@dataclass(slots=True)
class ActionResult:
    html: str | None = None
    js: str | None = None
    signals: dict[str, Any] = field(default_factory=dict)
    toasts: list[Any] = field(default_factory=list)
    redirect_to: str | None = None
    target: str | None = None
    swap: str | None = None
    swap_delay: int | None = None
    settle_delay: int | None = None
    transition: bool = False
    focus: str | None = None
    push_url: str | None = None
    replace_url: str | None = None
    strict_targets: bool | None = None
    oob: Any = field(default_factory=dict)
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)


def action(
    func_or_name: Callable[..., Any] | str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]] | Callable[..., Any]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        action_name = func_or_name if isinstance(func_or_name, str) else func.__name__
        setattr(func, "_hyper_action", True)
        setattr(func, "_hyper_action_name", action_name)
        return func

    if callable(func_or_name):
        return decorator(func_or_name)

    return decorator
