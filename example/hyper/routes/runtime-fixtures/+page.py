from __future__ import annotations

import time

from django.utils.html import escape
from hyper.layouts.base import BaseLayout

from hyperdjango.actions import (
    Actions,
    Delete,
    Event,
    HTML,
    History,
    Redirect,
    Signal,
    Signals,
    Toast,
    action,
)


class PageView(BaseLayout):
    """Deterministic browser fixtures for the public HyperDjango runtime.

    The page is deliberately not linked from the example navigation.  It keeps
    browser-level checks focused on the framework contracts rather than on the
    visual presentation of an individual demo.
    """

    def get(self, request, **params):
        return {
            "redirected": request.GET.get("redirected") == "1",
            "state": request.GET.get("state", "initial"),
        }

    @action
    def apply_items(self, request, **params):
        return Actions(
            HTML(
                content='<span data-fixture="prepended">prepended</span>',
                target="#append-target",
                swap="prepend",
            ),
            HTML(
                content='<span data-fixture="appended">appended</span>',
                target="#append-target",
                swap="append",
            ),
            HTML(
                content='<span data-fixture="before">before</span>',
                target="#swap-marker",
                swap="before",
            ),
            HTML(
                content='<span data-fixture="after">after</span>',
                target="#swap-marker",
                swap="after",
            ),
            HTML(
                content='<div id="outer-target" data-fixture="outer">outer replacement</div>',
                target="#outer-target",
                swap="outer",
            ),
            HTML(
                content='<strong data-fixture="inner">inner replacement</strong>',
                target="#inner-target",
                swap="inner",
            ),
            HTML(
                content='<span data-fixture="ignored">ignored</span>',
                target="#none-target",
                swap="none",
            ),
            Delete(target="#delete-target"),
            Event(
                name="runtime-fixture:event",
                payload={"message": "delivered"},
                target="#event-target",
            ),
            Toast(
                payload={
                    "type": "success",
                    "title": "Fixture complete",
                    "message": "Every typed action item was applied.",
                }
            ),
            History(replace_url="/runtime-fixtures/?state=updated"),
        )

    @action
    def redirect(self, request, **params):
        return Redirect(url="/runtime-fixtures/?redirected=1")

    @action
    def slow_loading(self, request, **params):
        time.sleep(1.5)
        return HTML(
            content='<p data-fixture="loading-result">finished</p>',
            target="#loading-result",
            swap="inner",
        )

    @action
    def alpine_options(self, request, value="", **params):
        return HTML(
            content=f'<p data-fixture="alpine-options">{escape(str(value))}</p>',
            target="#alpine-options-result",
            swap="inner",
        )

    @action
    def concurrent_append(self, request, label="", **params):
        time.sleep(0.15)
        return HTML(
            content=f'<li data-fixture="concurrent">{escape(str(label))}</li>',
            target="#concurrent-results",
            swap="append",
        )

    @action
    def focus_after_swap(self, request, **params):
        return HTML(
            content='<input id="fixture-focused" value="focused" />',
            target="#focus-result",
            swap="inner",
            focus="#fixture-focused",
            swap_delay=50,
            settle_delay=50,
            transition=True,
        )

    @action
    def missing_target(self, request, **params):
        return HTML(
            content="<p>missing target</p>",
            target="#fixture-target-does-not-exist",
            swap="inner",
            strict_targets=True,
        )

    @action
    def patch_signals(self, request, **params):
        return Actions(
            Signal(name="fixtureCount", value=1),
            Signals(values={"fixtureMessage": "patched", "$fixtureGlobal": "global"}),
        )
