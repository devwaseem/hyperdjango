from __future__ import annotations

from hyper.layouts.base import BaseLayout

from hyperdjango.actions import Signal, Signals, Toast, action


class PageView(BaseLayout):
    def get(self, request, **params):
        global_count = int(request.session.get("global_count", 0))
        return {"global_count": global_count}

    @action
    def increment_both(self, request, current=0, **params):
        local_count = int(current) + 1
        global_count = int(request.session.get("global_count", 0)) + 1
        request.session["global_count"] = global_count
        return [Signals(values={"count": local_count, "$count": global_count})]

    @action
    def reset_global(self, request, **params):
        request.session["global_count"] = 0
        return [
            Signal(name="$count", value=0),
            Toast(
                payload={
                    "type": "info",
                    "title": "Reset",
                    "message": "Global count reset.",
                }
            ),
        ]
