from hyper.layouts.dashboard import DashboardLayout


class DashboardSettingsPage(DashboardLayout):
    def get(self, request, **params):
        return {
            "settings": [
                "Notifications",
                "Security",
                "Billing",
            ]
        }
