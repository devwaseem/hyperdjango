from __future__ import annotations

from hyperdjango.actions import History, HTML, action

from hyper.layouts.base import BaseLayout


class PageView(BaseLayout):
    STATES = {
        "home": {
            "label": "Home state",
            "description": "This is the initial server-rendered state for /history-demo.",
            "tone": "#f8fafc",
        },
        "alpha": {
            "label": "Alpha state",
            "description": "This state was pushed by a HyperDjango action.",
            "tone": "#ecfeff",
        },
        "beta": {
            "label": "Beta state",
            "description": "This is another pushed history entry.",
            "tone": "#fef3c7",
        },
    }

    def get(self, request, **params):
        step = self._step(request.GET.get("step"))
        return {
            "step": step,
            "state": self.STATES[step],
        }

    @action
    def go(self, request, step="home", **params):
        step = self._step(step)
        url = "/history-demo/" if step == "home" else f"/history-demo/?step={step}"
        return [
            HTML(
                content=self.render(
                    request=request,
                    relative_template_name="partials/state.html",
                    context_updates={"step": step, "state": self.STATES[step]},
                ),
                target="#history-state",
                swap="outer",
            ),
            History(push_url=url),
        ]

    def _step(self, value):
        value = str(value or "home")
        if value not in self.STATES:
            return "home"
        return value
