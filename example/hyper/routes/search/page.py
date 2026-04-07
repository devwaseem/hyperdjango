from __future__ import annotations

import time

from hyper.layouts.base import BaseLayout

from hyperdjango.actions import action

NAMES = [
    "John",
    "Jane",
    "Bob",
    "Alice",
    "Carol",
    "Dave",
    "Eve",
    "Frank",
    "Grace",
    "Heidi",
    "Ivan",
    "Judy",
    "Kevin",
    "Laura",
    "Michael",
    "Nina",
    "Oliver",
    "Peter",
    "Queen",
    "Raymond",
    "Susan",
    "Thomas",
    "Ursula",
    "Victor",
    "William",
    "Xavier",
    "Yasmin",
    "Zachary",
]


class PageView(BaseLayout):
    def get(self, request, **params):
        return {"results": []}

    @action
    def search(self, request, q="", **params):
        query = str(q).strip().lower()
        if not query:
            return self.action_response(
                html=self.render(
                    request=request,
                    relative_template_name="partials/results.html",
                    context_updates={"results": []},
                ),
                target="#results",
                swap="inner",
                replace_url="/search",
            )

        time.sleep(2)
        results = [name for name in NAMES if query in name.lower()]
        if not results:
            return self.action_response(
                html=self.render(
                    request=request,
                    relative_template_name="partials/no_result.html",
                ),
                target="#results",
                swap="inner",
                replace_url="/search",
            )

        return self.action_response(
            html=self.render(
                request=request,
                relative_template_name="partials/results.html",
                context_updates={"results": results},
            ),
            target="#results",
            swap="inner",
            replace_url=f"/search?q={query}",
        )
