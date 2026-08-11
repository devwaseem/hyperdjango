from django.apps import AppConfig


class HyperDjangoDevtoolsConfig(AppConfig):
    name = "hyperdjango.integrations.devtools"
    label = "hyperdjango_devtools"
    verbose_name = "HyperDjango Debug Toolbar"

    def ready(self) -> None:
        from hyperdjango.integrations.devtools import checks  # noqa: F401
