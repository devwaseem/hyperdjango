from django.apps import AppConfig


class HyperDjangoDebugToolbarConfig(AppConfig):
    name = "hyperdjango.integrations.debug_toolbar"
    label = "hyperdjango_debug_toolbar"
    verbose_name = "HyperDjango Debug Toolbar"

    def ready(self) -> None:
        from hyperdjango.integrations.debug_toolbar import checks  # noqa: F401
