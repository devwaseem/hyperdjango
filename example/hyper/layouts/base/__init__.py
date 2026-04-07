from hyperdjango.page import HyperView


class BaseLayout(HyperView):
    def __init__(self) -> None:
        super().__init__()
        self.title = "HyperDjango Example"
