from hyperdjango.actions import action
from hyperdjango.page import HyperView


class BaseLayout(HyperView):
    pass


class DemoPage(BaseLayout):
    @action
    def save(self, request):
        return "ok"


def test_action_registration() -> None:
    page = DemoPage()
    action_method = page.get_action("save")
    assert action_method is not None
    assert action_method.__name__ == "save"
