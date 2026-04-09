from __future__ import annotations

from hyper.layouts.base import BaseLayout

from hyperdjango.actions import HTML, LoadJS, action


class PageView(BaseLayout):
    def get(self, request, **params):
        return {
            "modal_open": False,
            "modal_message": "This partial was rendered from a directory relative to the page, and its entry.ts was loaded with it.",
        }

    @action
    def open_modal(self, request, **params):
        partial = self.render_template(
            "partials/confirm_modal",
            request=request,
            context_updates={
                "title": "Standalone partial modal",
                "message": "This modal shell is extended by a concrete partial, then returned as typed SSE action items.",
                "confirm_label": "Looks good",
            },
        )
        items = [HTML(content=partial.html, target="#modal-root", swap="inner")]
        if partial.js:
            items.append(LoadJS(src=partial.js))
        return items
