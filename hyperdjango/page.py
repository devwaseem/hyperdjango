from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Any, Generator, cast

from django.http import HttpRequest
from django.template import RequestContext, loader
from render_block import render_block_to_string

from hyperdjango.actions import ActionResult
from hyperdjango.assets import (
    AssetTag,
    ModulePreloadTag,
    ModuleTag,
    StyleSheetTag,
    ViteAssetResolver,
)
from hyperdjango.conf import get_frontend_dir, get_vite_dev_server_url, is_dev_env
from hyperdjango.runtime.dispatcher import dispatch_page


class FileNotLoadedFromViteError(Exception):
    def __init__(self, file_name: str) -> None:
        super().__init__(f"{file_name} was not included in Vite manifest")


class PageTemplateMeta(type):
    def __init__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
    ) -> None:
        super().__init__(name, bases, namespace)

        if cls.__name__ == "PageTemplate":
            return

        cls._assets = {
            "stylesheets": [],
            "preloads": [],
            "head": [],
            "body": [],
        }

        head_files = ["entry.head.js", "entry.head.ts"]
        body_files = ["entry.js", "entry.ts"]

        if is_dev_env():
            cls._assets["head"].append(
                ModuleTag(src=f"{get_vite_dev_server_url()}@vite/client")
            )

        seen: set[AssetTag] = set()
        resolver = getattr(cls, "resolve_import")
        for files, section in ((head_files, "head"), (body_files, "body")):
            for file_name in files:
                try:
                    tags = resolver(file_name=file_name)
                except FileNotFoundError:
                    continue
                for tag in tags:
                    if tag in seen:
                        continue
                    if isinstance(tag, StyleSheetTag):
                        cls._assets["stylesheets"].append(tag)
                    elif isinstance(tag, ModulePreloadTag):
                        cls._assets["preloads"].append(tag)
                    elif isinstance(tag, ModuleTag):
                        cls._assets[section].append(tag)
                    seen.add(tag)


class PageTemplate(metaclass=PageTemplateMeta):
    _assets: dict[str, list[AssetTag]] = {}

    def __init__(self) -> None:
        self.stylesheets: list[StyleSheetTag] = []
        self.preload_imports: list[ModulePreloadTag] = []
        self.head_imports: list[ModuleTag] = []
        self.body_imports: list[ModuleTag] = []
        self._collect_inherited_assets()

    def get_context(self) -> dict[str, Any]:
        return {"page": self}

    def render(
        self,
        *,
        request: HttpRequest,
        relative_template_name: str = "",
        context_updates: dict[str, Any] | None = None,
    ) -> str:
        template_name = (
            self.get_template_name()
            if not relative_template_name
            else self.get_relative_template_name(relative_template_name)
        )
        context = self.get_context()
        context.update(context_updates or {})
        return str(
            loader.get_template(template_name=template_name).render(
                context=context,
                request=request,
            )
        )

    def render_block(
        self,
        *,
        block_name: str,
        request: HttpRequest,
        relative_template_name: str = "",
        context_updates: dict[str, Any] | None = None,
    ) -> str:
        template_name = (
            self.get_template_name()
            if not relative_template_name
            else self.get_relative_template_name(relative_template_name)
        )
        context = self.get_context()
        context.update(context_updates or {})
        return cast(
            str,
            render_block_to_string(
                template_name=template_name,
                block_name=block_name,
                context=RequestContext(request, context),
                request=request,
            ),
        )

    @classmethod
    def get_template_name(cls) -> str:
        return cls.get_relative_template_name("index.html")

    @classmethod
    def get_relative_template_name(cls, name: str) -> str:
        base_path = cls._get_base_path()
        return cls._to_template_name(base_path / name)

    def _collect_inherited_assets(self) -> None:
        collected: dict[str, list[AssetTag]] = {
            "stylesheets": [],
            "preloads": [],
            "head": [],
            "body": [],
        }
        seen: set[AssetTag] = set()
        for cls in self.__class__.__mro__:
            assets = getattr(cls, "_assets", None)
            if not assets:
                continue
            for key, values in assets.items():
                for tag in values:
                    if tag in seen:
                        continue
                    collected[key].append(tag)
                    seen.add(tag)
        self.stylesheets = cast(list[StyleSheetTag], collected["stylesheets"])
        self.preload_imports = cast(list[ModulePreloadTag], collected["preloads"])
        self.head_imports = cast(list[ModuleTag], collected["head"])
        self.body_imports = cast(list[ModuleTag], collected["body"])

    @classmethod
    def resolve_import(cls, *, file_name: str) -> Generator[AssetTag, None, None]:
        base = cls._get_base_path()
        path = base / file_name
        if not path.exists():
            raise FileNotFoundError(f"file {file_name} not found")
        manifest_name = cls._to_manifest_name(path)
        if not manifest_name:
            raise FileNotLoadedFromViteError(file_name=file_name)
        return ViteAssetResolver.get_imports(file=manifest_name)

    @classmethod
    def _get_base_path(cls) -> Path:
        return Path(cls._get_file_path()).parent

    @classmethod
    def _get_file_path(cls) -> str:
        mod = sys.modules.get(cls.__module__)
        path = getattr(mod, "__file__", None) if mod is not None else None
        if not path:
            path = inspect.getfile(cls)
        if not path:
            raise RuntimeError(f"Cannot determine file path for {cls}")
        return str(path)

    @classmethod
    def _to_template_name(cls, file_path: Path) -> str:
        frontend_dir = get_frontend_dir()
        if not file_path.exists():
            raise FileNotFoundError(file_path)
        return str(file_path.relative_to(frontend_dir))

    @classmethod
    def _to_manifest_name(cls, file_path: Path) -> str | None:
        frontend_dir = get_frontend_dir()
        if not file_path.exists():
            return None
        return str(file_path.relative_to(frontend_dir.parent))


class HyperActionMixin:
    _actions: dict[str, Any] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._actions = {}
        for _, value in inspect.getmembers(cls):
            if callable(value) and getattr(value, "_hyper_action", False):
                action_name = cast(str, getattr(value, "_hyper_action_name"))
                cls._actions[action_name] = value

    def get_action(self, name: str) -> Any | None:
        for cls in self.__class__.__mro__:
            actions = getattr(cls, "_actions", {})
            if name in actions:
                return actions[name].__get__(self, self.__class__)
        return None

    def action_response(
        self,
        *,
        html: str | None = None,
        signals: dict[str, Any] | None = None,
        toast: Any | None = None,
        toasts: list[Any] | None = None,
        target: str | None = None,
        swap: str | None = None,
        swap_delay: int | None = None,
        settle_delay: int | None = None,
        transition: bool = False,
        focus: str | None = None,
        push_url: str | None = None,
        replace_url: str | None = None,
        strict_targets: bool | None = None,
        oob: Any | None = None,
        status: int = 200,
        headers: dict[str, str] | None = None,
        action: str | None = None,
        request: HttpRequest | None = None,
        context_updates: dict[str, Any] | None = None,
    ) -> ActionResult:
        rendered_html = html
        if rendered_html is None and action and request is not None:
            if not hasattr(self, "render_block"):
                raise RuntimeError(
                    "action_response(action=...) requires render_block on the class"
                )
            rendered_html = cast(Any, self).render_block(
                request=request,
                block_name=action,
                context_updates=context_updates,
            )

        toast_items = list(toasts or [])
        if toast is not None:
            toast_items.append(toast)

        return ActionResult(
            html=rendered_html,
            signals=signals or {},
            toasts=toast_items,
            target=target,
            swap=swap,
            swap_delay=swap_delay,
            settle_delay=settle_delay,
            transition=transition,
            focus=focus,
            push_url=push_url,
            replace_url=replace_url,
            strict_targets=strict_targets,
            oob=oob or {},
            status=status,
            headers=headers or {},
        )


class HyperView(PageTemplate, HyperActionMixin):
    _actions: dict[str, Any] = {}

    def dispatch(self, request: HttpRequest, **params: Any):
        return dispatch_page(self, request, **params)

    def get(self, request: HttpRequest, **params: Any) -> dict[str, Any]:
        return self.get_context()


class Page(HyperView):
    """Backward-compatible alias for HyperView."""
