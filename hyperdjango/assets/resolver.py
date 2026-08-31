from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generator

from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import SafeString

from hyperdjango.assets.manifest import ManifestEntry, load_manifest
from hyperdjango.conf import get_vite_dev_server_url, is_dev_env


@dataclass(frozen=True)
class AssetTag(ABC):
    src: str

    @property
    def resolved_src(self) -> str:
        return self.src

    @abstractmethod
    def render(self, nonce: str | None = None) -> SafeString:
        raise NotImplementedError


@dataclass(frozen=True)
class ModulePreloadTag(AssetTag):
    def render(self, nonce: str | None = None) -> SafeString:
        return format_html('<link rel="modulepreload" href="{}" />', self.src)


@dataclass(frozen=True)
class ModuleTag(AssetTag):
    def render(self, nonce: str | None = None) -> SafeString:
        nonce_attr = format_html(' nonce="{}"', nonce) if nonce else ""
        return format_html(
            '<script type="module" src="{}"{}></script>',
            self.resolved_src,
            nonce_attr,
        )


@dataclass(frozen=True)
class ViteDevServerModuleTag(ModuleTag):
    @property
    def resolved_src(self) -> str:
        return f"{get_vite_dev_server_url()}{self.src}"


@dataclass(frozen=True)
class StyleSheetTag(AssetTag):
    def render(self, nonce: str | None = None) -> SafeString:
        nonce_attr = format_html(' nonce="{}"', nonce) if nonce else ""
        return format_html(
            '<link rel="stylesheet" href="{}"{}>', self.src, nonce_attr
        )


class AssetResolver(ABC):
    @abstractmethod
    def get_imports(self, file: str) -> Generator[AssetTag, None, None]:
        raise NotImplementedError


class ViteDevServerAssetResolver(AssetResolver):
    def get_imports(self, file: str) -> Generator[AssetTag, None, None]:
        yield ViteDevServerModuleTag(src=file)


class ManifestAssetResolver(AssetResolver):
    def __init__(self, entries: dict[str, ManifestEntry]) -> None:
        self.entries = entries

    def get_imports(self, file: str) -> Generator[AssetTag, None, None]:
        if file not in self.entries:
            raise FileNotFoundError(f"{file} does not exist in Vite manifest")
        entry = self.entries[file]

        for js_file in entry.import_list:
            js_entry = self.entries[js_file]
            yield ModulePreloadTag(src=static(js_entry.file))

        yield from self._stylesheets(entry)
        yield ModuleTag(src=static(entry.file))

    def _stylesheets(
        self, entry: ManifestEntry
    ) -> Generator[StyleSheetTag, None, None]:
        for css_file in entry.css_list:
            yield StyleSheetTag(src=static(css_file))
        for imported in entry.import_list:
            yield from self._stylesheets(self.entries[imported])


class ViteAssetResolver:
    @staticmethod
    def get_imports(file: str) -> Generator[AssetTag, None, None]:
        resolver: AssetResolver
        if is_dev_env():
            resolver = ViteDevServerAssetResolver()
        else:
            resolver = ManifestAssetResolver(load_manifest())
        yield from resolver.get_imports(file)
