from hyperdjango.page import Page


class BaseLayout(Page):
    def __init__(self) -> None:
        super().__init__()
        self.title = "HyperDjango Example"
