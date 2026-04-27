from django.apps import AppConfig

try:
    from django.utils import autoreload
except Exception:  # pragma: no cover - import should be available under Django
    autoreload = None

WATCH_GLOBS = (
    "**/*.py",
    "**/*.html",
    "**/*.js",
    "**/*.ts",
    "**/*.css",
    "**/*.json",
)


class HyperDjangoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"  # type: ignore[assignment]
    name = "hyperdjango"

    def ready(self) -> None:
        return


def _watch_hyper_frontend(sender, **kwargs) -> None:
    try:
        from hyperdjango.conf import get_frontend_dir

        frontend_dir = get_frontend_dir()
        watch_dir = getattr(sender, "watch_dir", None)
        if not callable(watch_dir):
            return
        for glob in WATCH_GLOBS:
            watch_dir(frontend_dir, glob)
    except Exception:
        # Autoreload registration should never break app startup.
        return


if autoreload is not None:
    try:
        autoreload.autoreload_started.connect(
            _watch_hyper_frontend,
            dispatch_uid="hyperdjango.watch_hyper_frontend",
        )
    except Exception:
        pass
