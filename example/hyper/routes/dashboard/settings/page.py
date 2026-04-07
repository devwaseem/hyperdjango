from hyper.layouts.dashboard import DashboardLayout


class PageView(DashboardLayout):
    def get(self, request, **params):
        return {
            "settings": [
                "Notifications",
                "Security",
                "Billing",
            ]
        }
