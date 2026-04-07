from __future__ import annotations

from hyperdjango.actions import action

from hyper.layouts.base import BaseLayout


class HomePage(BaseLayout):
    TIPS = [
        "Use folder names to define URLs.",
        "Actions can return HTML, signals, and toasts.",
        "Server can choose target and swap strategy.",
        "Enable View Transitions per action call.",
    ]

    def get(self, request, **params):
        editable_text = self._current_text(request)
        tip_index = self._tip_index(request)
        return {
            "headline": "HyperDjango file routing is live",
            "description": "This page is served from hyper/routes/index/page.py",
            "editable_text": editable_text,
            "tip_index": tip_index,
            "tip_text": self.TIPS[tip_index],
            "examples": [
                {"url": "/about", "label": "Static route: about"},
                {"url": "/blog/hello-world", "label": "Dynamic route: blog/[slug]"},
                {
                    "url": "/docs/getting-started/install",
                    "label": "Catch-all route: docs/[...path]",
                },
                {"url": "/pricing", "label": "Route group: (marketing)/pricing"},
                {"url": "/dashboard", "label": "Nested layout: dashboard/index"},
                {"url": "/dashboard/settings", "label": "Nested layout + static child"},
                {"url": "/todos", "label": "SPA-like todos with partial actions"},
                {"url": "/signals", "label": "Signals: local vs global ($key)"},
                {
                    "url": "/template-card",
                    "label": "Template package used from custom Django view",
                },
                {"url": "/profile", "label": "Django form enhanced with hyper-form"},
            ],
        }

    @action
    def increment(self, request, current=0, **params):
        current = int(current)
        return self.action_response(signals={"count": current + 1})

    @action
    def show_editor(self, request, **params):
        return self.action_response(
            html=self.render(
                request=request,
                relative_template_name="partials/editor_form.html",
                context_updates={"editable_text": self._current_text(request)},
            ),
            target="#editor",
            oob={
                "#flash": self.render(
                    request=request,
                    relative_template_name="partials/flash.html",
                    context_updates={"message": "Editing..."},
                )
            },
        )

    @action
    def save_text(self, request, text="", **params):
        request.session["editable_text"] = str(text)
        return self.action_response(
            html=self.render(
                request=request,
                relative_template_name="partials/text_view.html",
                context_updates={"editable_text": self._current_text(request)},
            ),
            toast={"type": "success", "title": "Saved", "message": "Text updated."},
            target="#editor",
            oob={
                "#flash": self.render(
                    request=request,
                    relative_template_name="partials/flash.html",
                    context_updates={"message": "Saved."},
                )
            },
        )

    @action
    def show_text(self, request, **params):
        return self.action_response(
            html=self.render(
                request=request,
                relative_template_name="partials/text_view.html",
                context_updates={"editable_text": self._current_text(request)},
            ),
            target="#editor",
            oob={
                "#flash": self.render(
                    request=request,
                    relative_template_name="partials/flash.html",
                    context_updates={"message": "Canceled."},
                )
            },
        )

    @action
    def next_tip(self, request, **params):
        tip_index = (self._tip_index(request) + 1) % len(self.TIPS)
        request.session["tip_index"] = tip_index
        return self.action_response(
            html=self.render(
                request=request,
                relative_template_name="partials/tip_card.html",
                context_updates={
                    "tip_index": tip_index,
                    "tip_text": self.TIPS[tip_index],
                },
            ),
            target="#tip-card",
            transition=True,
        )

    def _current_text(self, request) -> str:
        return str(
            request.session.get(
                "editable_text", "Edit me from the server-rendered form."
            )
        )

    def _tip_index(self, request) -> int:
        raw = request.session.get("tip_index", 0)
        try:
            idx = int(raw)
        except (TypeError, ValueError):
            idx = 0
        return idx % len(self.TIPS)
