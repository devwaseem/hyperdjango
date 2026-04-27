from __future__ import annotations

import asyncio

from hyper.layouts.base import BaseLayout

from hyperdjango.actions import HTML, Signal, Toast, action


class PageView(BaseLayout):
    async def get(self, request, **params):
        return {
            "stream": {
                "phase": "Idle",
                "progress": 0,
                "done": False,
            }
        }

    @action
    async def run_demo(self, request, **params):
        yield HTML(
            content="<div style='padding: 0.75rem 0.9rem; border: 1px dashed #cbd5e1; border-radius: 10px; color: #475569;'>Stream started...</div>",
            target="#stream-log",
            swap="inner",
        )
        yield Signal(
            name="stream",
            value={
                "phase": "Connecting to server stream...",
                "progress": 0,
                "done": False,
            },
        )

        for step in range(1, 6):
            await asyncio.sleep(1)
            percent = step * 20
            yield Signal(
                name="stream",
                value={
                    "phase": f"Processing step {step} of 5",
                    "progress": percent,
                    "done": False,
                },
            )
            yield HTML(
                content=self.render(
                    request=request,
                    relative_template_name="partials/log_item.html",
                    context_updates={
                        "step": step,
                        "percent": percent,
                    },
                ),
                target="#stream-log",
                swap="append",
            )

        yield Signal(
            name="stream",
            value={
                "phase": "Complete",
                "progress": 100,
                "done": True,
            },
        )
        yield Toast(
            payload={
                "type": "success",
                "title": "Stream complete",
                "message": "The server pushed five incremental updates over one action request.",
            }
        )
