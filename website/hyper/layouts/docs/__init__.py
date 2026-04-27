from __future__ import annotations

from hyper.layouts.base import BaseLayout


class DocsLayout(BaseLayout):
    def __init__(self) -> None:
        super().__init__(title="HyperDjango Docs")
