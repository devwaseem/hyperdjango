from typing import Any, override

from django.conf import settings
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
        context.setdefault("title", self.title)
        context.setdefault("meta_description", self.title)
        context.setdefault(
            "canonical_url", request.build_absolute_uri(request.path)
        )
        context.setdefault("meta_robots", "index,follow")
        context.setdefault("json_ld", "")
        context.setdefault("site_name", "HyperDjango")
        context.setdefault(
            "site_url",
            getattr(
                settings, "SITE_URL", request.build_absolute_uri("/")
            ).rstrip("/"),
        )
        context["github_repo_url"] = github.repo_url
        context["github_stars_label"] = github.stars_label
        return context
