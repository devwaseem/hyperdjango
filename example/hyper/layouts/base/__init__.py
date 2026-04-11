from typing import Any, override

from django.http import HttpRequest

from hyperdjango.page import HyperView


class BaseLayout(HyperView):
    def __init__(self) -> None:
        super().__init__()
        self.title = "HyperDjango Example"

    @override
    def get_context(self, request: HttpRequest) -> dict[str, Any]:
        context = super().get_context(request)
        context["title"] = self.title
        return context
