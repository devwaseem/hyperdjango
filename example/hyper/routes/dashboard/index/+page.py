from hyperdjango.actions import action

from hyper.layouts.dashboard import DashboardLayout


class PageView(DashboardLayout):
    def get(self, request, **params):
        return {
            "headline": "Dashboard overview",
            "status": "All systems operational",
        }

    @action
    def pulse(self, request, pulse=0, **params):
        current = int(pulse)
        return self.action_response(signals={"dashboard": {"pulse": current + 1}})
