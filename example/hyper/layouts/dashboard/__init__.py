from hyper.layouts.base import BaseLayout


class DashboardLayout(BaseLayout):
    def __init__(self) -> None:
        super().__init__()
        self.title = "Dashboard"
