from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Final
from urllib.error import URLError
from urllib.request import Request, urlopen


GITHUB_REPO_URL: Final[str] = "https://github.com/devwaseem/hyperdjango"
GITHUB_REPO_API_URL: Final[str] = "https://api.github.com/repos/devwaseem/hyperdjango"
CACHE_TTL_SECONDS: Final[int] = 600


@dataclass(slots=True)
class GitHubStats:
    stars_label: str
    repo_url: str = GITHUB_REPO_URL


_cache: GitHubStats | None = None
_cache_expires_at: float = 0.0


def get_github_stats() -> GitHubStats:
    global _cache, _cache_expires_at

    now = time.time()
    if _cache is not None and now < _cache_expires_at:
        return _cache

    stats = _fetch_github_stats()
    _cache = stats
    _cache_expires_at = now + CACHE_TTL_SECONDS
    return stats


def _fetch_github_stats() -> GitHubStats:
    request = Request(
        GITHUB_REPO_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "hyperdjango-website",
        },
    )

    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, ValueError, URLError):
        return GitHubStats(stars_label="GitHub")

    stars = payload.get("stargazers_count")
    if not isinstance(stars, int):
        return GitHubStats(stars_label="GitHub")
    return GitHubStats(stars_label=_format_stars(stars))


def _format_stars(stars: int) -> str:
    if stars < 1000:
        return str(stars)
    if stars < 10_000:
        value = f"{stars / 1000:.1f}".rstrip("0").rstrip(".")
        return f"{value}k"
    return f"{stars // 1000}k"
