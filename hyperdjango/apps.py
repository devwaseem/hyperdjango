from django.apps import AppConfig


class HyperDjangoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"  # type: ignore[assignment]
    name = "hyperdjango"

    def ready(self) -> None:
        try:
            from django.utils import autoreload

            from hyperdjango.conf import get_frontend_dir

            watch_dir = getattr(autoreload, "watch_dir", None)
            if not callable(watch_dir):
                return
            frontend_dir = get_frontend_dir()
            watch_dir(
                frontend_dir,
                "**/*.{py,html,js,ts,css,json}",
            )
        except Exception:
            # Autoreload registration should never break app startup.
            return
