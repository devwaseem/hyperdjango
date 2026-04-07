from __future__ import annotations

from hyper.layouts.base import BaseLayout

from hyperdjango.actions import action


class PageView(BaseLayout):
    def get(self, request, **params):
        global_count = int(request.session.get("global_count", 0))
        return {"global_count": global_count}

    @action
    def increment_both(self, request, current=0, **params):
        local_count = int(current) + 1
        global_count = int(request.session.get("global_count", 0)) + 1
        request.session["global_count"] = global_count
        return self.action_response(
            signals={
                "count": local_count,
                "$count": global_count,
            }
        )

    @action
    def reset_global(self, request, **params):
        request.session["global_count"] = 0
        return self.action_response(
            signals={
                "$count": 0,
            },
            toast={"type": "info", "title": "Reset", "message": "Global count reset."},
        )
