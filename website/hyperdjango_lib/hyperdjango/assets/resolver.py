from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generator

from django.templatetags.static import static

from hyperdjango.assets.manifest import ManifestEntry, load_manifest
from hyperdjango.conf import get_vite_dev_server_url, is_dev_env


@dataclass(frozen=True)
class AssetTag(ABC):
    src: str

    @abstractmethod
    def render(self, nonce: str | None = None) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class ModulePreloadTag(AssetTag):
    def render(self, nonce: str | None = None) -> str:
        return f'<link rel="modulepreload" href="{self.src}" />'


@dataclass(frozen=True)
class ModuleTag(AssetTag):
    def render(self, nonce: str | None = None) -> str:
        nonce_attr = f' nonce="{nonce}"' if nonce else ""
        return f'<script type="module" src="{self.src}"{nonce_attr}></script>'


@dataclass(frozen=True)
class StyleSheetTag(AssetTag):
    def render(self, nonce: str | None = None) -> str:
        nonce_attr = f' nonce="{nonce}"' if nonce else ""
        return f'<link rel="stylesheet" href="{self.src}"{nonce_attr}>'


class AssetResolver(ABC):
    @abstractmethod
    def get_imports(self, file: str) -> Generator[AssetTag, None, None]:
        raise NotImplementedError


class ViteDevServerAssetResolver(AssetResolver):
    def get_imports(self, file: str) -> Generator[AssetTag, None, None]:
        base = get_vite_dev_server_url()
        yield ModuleTag(src=f"{base}{file}")


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
