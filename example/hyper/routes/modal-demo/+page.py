from __future__ import annotations

from hyper.layouts.base import BaseLayout

from hyperdjango.actions import action


class PageView(BaseLayout):
    def get(self, request, **params):
        return {
            "modal_open": False,
            "modal_message": "This partial was rendered from a directory relative to the page, and its entry.ts was loaded with it.",
        }

    @action
    def open_modal(self, request, **params):
        return self.action_response(
            content=self.render_template(
                "partials/confirm_modal",
                request=request,
                context_updates={
                    "title": "Standalone partial modal",
                    "message": "This modal shell is extended by a concrete partial, then returned through action_response(content=...).",
                    "confirm_label": "Looks good",
                },
            ),
            target="#modal-root",
            swap="inner",
        )
