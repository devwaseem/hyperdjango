from django.apps import AppConfig


class HyperDjangoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"  # type: ignore[assignment]
    name = "hyperdjango"

    def ready(self) -> None:
        try:
            from django.utils import autoreload

            from hyperdjango.conf import get_frontend_dir

            frontend_dir = get_frontend_dir()

            def _watch_hyper_frontend(sender, **kwargs) -> None:
                watch_dir = getattr(sender, "watch_dir", None)
                if not callable(watch_dir):
                    return
                watch_dir(
                    frontend_dir,
                    "**/*.{py,html,js,ts,css,json}",
                )

            autoreload.autoreload_started.connect(
                _watch_hyper_frontend,
                dispatch_uid="hyperdjango.watch_hyper_frontend",
            )
        except Exception:
            # Autoreload registration should never break app startup.
            return
