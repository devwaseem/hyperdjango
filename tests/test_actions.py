import inspect

import pytest

from hyperdjango.actions import Action, Checkpoint, action
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
    assert isinstance(DemoPage.save, Action)
    assert list(inspect.signature(action_method).parameters) == ["request"]
    assert inspect.unwrap(action_method) is DemoPage.save.__wrapped__


@pytest.mark.parametrize(
    "name",
    ["queued", "build.ready", "step_2", "a" * 64],
)
def test_checkpoint_accepts_stable_wire_names(name: str) -> None:
    assert Checkpoint(name).name == name


@pytest.mark.parametrize(
    "name",
    ["", "has space", "has:colon", "line\nbreak", "é", "a" * 65, None],
)
def test_checkpoint_rejects_invalid_wire_names(name: str | None) -> None:
    with pytest.raises(ValueError, match="checkpoint name must match"):
        Checkpoint(name)  # type: ignore[arg-type]


def test_action_decorator_does_not_accept_server_retry_policy() -> None:
    with pytest.raises(TypeError, match="unexpected keyword argument 'retry'"):
        action(method="GET", retry=True)  # type: ignore[call-overload]
