from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import update_wrapper
from inspect import Parameter, Signature, signature
from typing import Any, Callable, Generic, Literal, ParamSpec, TypeAlias, TypeVar, cast
from urllib.parse import urlencode, urlsplit

from hyperdjango.integrations.alpine.actions import Signal, Signals
from hyperdjango.sse import validate_checkpoint_name


SwapMode: TypeAlias = Literal[
    "inner",
    "outer",
    "before",
    "after",
    "prepend",
    "append",
    "delete",
    "none",
]
ActionMethod: TypeAlias = Literal["GET", "POST"]

P = ParamSpec("P")
R = TypeVar("R")


@dataclass(frozen=True, slots=True)
class ActionEndpoint:
    """A Django route used by a cross-endpoint action handoff."""

    route: str
    route_kwargs: dict[str, Any] = field(default_factory=dict)
    query: dict[str, Any] = field(default_factory=dict)

    def resolve(self, action: Action[P, R] | BoundAction[P, R]) -> str:
        from django.urls import resolve, reverse

        url = reverse(self.route, kwargs=self.route_kwargs or None)
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc:
            raise ValueError("ActionEndpoint must resolve to an application-local URL")

        match = resolve(parsed.path)
        page_class = getattr(match.func, "view_class", None)
        owner = action.owner
        if page_class is None or owner is None:
            raise ValueError(
                f"Cannot validate action ownership for route '{self.route}'"
            )
        if not issubclass(page_class, owner):
            raise ValueError(
                f"Action '{action.action_name}' does not belong to route "
                f"'{self.route}' ({page_class.__name__})"
            )

        if self.query:
            separator = "&" if parsed.query else "?"
            url = f"{url}{separator}{urlencode(self.query, doseq=True)}"
        return url


class Action(Generic[P, R]):
    """Callable descriptor produced by :func:`action`."""

    _hyper_action = True

    def __init__(
        self,
        func: Callable[P, R],
        *,
        name: str,
        method: ActionMethod | None,
    ) -> None:
        self.func = func
        self.action_name = name
        self.method = method
        self.owner: type[Any] | None = None
        self._hyper_action_name = name
        self._hyper_action_method = method
        update_wrapper(self, func)

    def __set_name__(self, owner: type[Any], name: str) -> None:
        self.owner = owner

    def __get__(
        self, instance: Any | None, owner: type[Any] | None = None
    ) -> Action[P, R] | BoundAction[P, R]:
        if instance is None:
            return self
        return BoundAction(self, instance)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        return self.func(*args, **kwargs)

    def at(
        self,
        route: str,
        *,
        route_kwargs: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> ActionSwitchBuilder[P, R]:
        return ActionSwitchBuilder(
            self,
            ActionEndpoint(
                route=route,
                route_kwargs=route_kwargs or {},
                query=query or {},
            ),
        )

    def switch_to(self, *args: Any, **kwargs: Any) -> SwitchAction:
        return ActionSwitchBuilder(self).switch_to(*args, **kwargs)

    def bind_switch_arguments(
        self,
        *args: Any,
        implicit: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        parameters = list(signature(self.func).parameters.values())
        if len(parameters) < 2:
            raise TypeError(
                f"Action '{self.action_name}' must accept self and request arguments"
            )
        action_signature = Signature(parameters[2:])
        explicit_bound = action_signature.bind_partial(*args, **kwargs)
        explicit: dict[str, Any] = {}
        for name, value in explicit_bound.arguments.items():
            parameter = action_signature.parameters[name]
            if parameter.kind is Parameter.VAR_POSITIONAL:
                raise TypeError(
                    "SwitchAction destinations do not support variadic positional "
                    "arguments"
                )
            if parameter.kind is Parameter.VAR_KEYWORD:
                explicit.update(value)
            else:
                explicit[name] = value

        implicit = implicit or {}
        duplicates = explicit.keys() & implicit.keys()
        if duplicates:
            names = ", ".join(sorted(duplicates))
            raise TypeError(
                f"SwitchAction arguments duplicate route parameters: {names}"
            )
        action_signature.bind(**implicit, **explicit)
        return explicit


class BoundAction(Generic[P, R]):
    """An action reference bound to a page instance."""

    _hyper_action = True

    def __init__(self, action: Action[P, R], instance: Any) -> None:
        self.action = action
        self.instance = instance
        self.action_name = action.action_name
        self.method = action.method
        self.owner = action.owner
        self._hyper_action_name = action.action_name
        self._hyper_action_method = action.method
        self.__self__ = instance
        update_wrapper(self, action.func)
        parameters = list(signature(action.func).parameters.values())
        self.__signature__ = Signature(parameters[1:])

    def __call__(self, *args: Any, **kwargs: Any) -> R:
        func = cast(Callable[..., R], self.action.func)
        return func(self.instance, *args, **kwargs)

    def at(
        self,
        route: str,
        *,
        route_kwargs: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> ActionSwitchBuilder[P, R]:
        return ActionSwitchBuilder(
            self,
            ActionEndpoint(
                route=route,
                route_kwargs=route_kwargs or {},
                query=query or {},
            ),
        )

    def switch_to(self, *args: Any, **kwargs: Any) -> SwitchAction:
        return ActionSwitchBuilder(self).switch_to(*args, **kwargs)

    def bind_switch_arguments(
        self,
        *args: Any,
        implicit: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if implicit is None:
            implicit = getattr(
                self.instance,
                "_hyper_action_route_params",
                {},
            )
        return self.action.bind_switch_arguments(
            *args,
            implicit=implicit,
            **kwargs,
        )


@dataclass(frozen=True, slots=True)
class ActionSwitchBuilder(Generic[P, R]):
    action: Action[P, R] | BoundAction[P, R]
    endpoint: ActionEndpoint | None = None

    def switch_to(self, *args: Any, **kwargs: Any) -> SwitchAction:
        implicit = self.endpoint.route_kwargs if self.endpoint else None
        switch = SwitchAction(
            action=self.action,
            arguments=self.action.bind_switch_arguments(
                *args,
                implicit=implicit,
                **kwargs,
            ),
            endpoint=self.endpoint,
        )
        switch.resolve()
        return switch


@dataclass(slots=True)
class HTML:
    content: str
    target: str | None = None
    swap: SwapMode = "outer"
    transition: bool = False
    focus: str | None = None
    swap_delay: int | None = None
    settle_delay: int | None = None
    strict_targets: bool | None = None


@dataclass(slots=True)
class Toast:
    payload: dict[str, Any]


@dataclass(slots=True)
class Event:
    name: str
    payload: dict[str, Any]
    target: str | None = None


@dataclass(slots=True)
class Delete:
    target: str


@dataclass(slots=True)
class Redirect:
    url: str


@dataclass(frozen=True, slots=True)
class Checkpoint:
    """Mark a completed stage in a resumable GET action stream."""

    name: str

    def __post_init__(self) -> None:
        validate_checkpoint_name(self.name)


@dataclass(slots=True)
class SwitchAction:
    """Terminate this action stream and start a separate client action.

    This is a command-to-query handoff, not an idempotency mechanism. The
    client determines whether the destination request may be retried.
    """

    action: Action[Any, Any] | BoundAction[Any, Any]
    arguments: dict[str, Any] = field(default_factory=dict)
    endpoint: ActionEndpoint | None = None

    def resolve(self) -> tuple[str, dict[str, Any], ActionMethod, str | None]:
        method = self.action.method
        if method is None:
            raise TypeError(
                f"Action '{self.action.action_name}' must declare method= "
                "before it can be used as a SwitchAction destination"
            )
        url = self.endpoint.resolve(self.action) if self.endpoint else None
        return (
            self.action.action_name,
            self.arguments,
            cast(ActionMethod, method),
            url,
        )


@dataclass(slots=True)
class History:
    push_url: str | None = None
    replace_url: str | None = None


@dataclass(slots=True)
class LoadJS:
    src: str


ActionItem = (
    Signal
    | Signals
    | HTML
    | Toast
    | Event
    | Delete
    | Redirect
    | Checkpoint
    | SwitchAction
    | History
    | LoadJS
)


@dataclass(slots=True, init=False)
class Actions:
    items: tuple[ActionItem, ...]

    def __init__(self, *items: ActionItem) -> None:
        self.items = items

    def __iter__(self) -> Iterator[ActionItem]:
        return iter(self.items)


@dataclass(slots=True)
class ActionResult:
    html: str | None = None
    js: str | None = None
    signals: dict[str, Any] = field(default_factory=dict)
    toasts: list[dict[str, Any]] = field(default_factory=list)
    redirect_to: str | None = None
    target: str | None = None
    swap: SwapMode | None = None
    swap_delay: int | None = None
    settle_delay: int | None = None
    transition: bool = False
    focus: str | None = None
    push_url: str | None = None
    replace_url: str | None = None
    strict_targets: bool | None = None
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)


def action(
    func_or_name: Callable[P, R] | str | None = None,
    *,
    method: ActionMethod | None = None,
) -> Callable[[Callable[P, R]], Action[P, R]] | Action[P, R]:
    normalized_method: ActionMethod | None = None
    if method is not None:
        raw_method = method.upper()
        if raw_method not in {"GET", "POST"}:
            raise ValueError("action method must be GET or POST")
        normalized_method = cast(ActionMethod, raw_method)

    def decorator(func: Callable[P, R]) -> Action[P, R]:
        action_name = func_or_name if isinstance(func_or_name, str) else func.__name__
        return Action(
            func,
            name=action_name,
            method=normalized_method,
        )

    if callable(func_or_name):
        return decorator(func_or_name)

    return decorator
