from typing import Any, override

from django.http import HttpRequest

from hyper.shared.github import get_github_stats
from hyperdjango.page import HyperView


class BaseLayout(HyperView):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title

    @override
    def get_context(self, request: HttpRequest) -> dict[str, Any]:
        context = super().get_context(request)
        github = get_github_stats()
        context["title"] = self.title
        context["github_repo_url"] = github.repo_url
        context["github_stars_label"] = github.stars_label
        return context
