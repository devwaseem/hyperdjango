from __future__ import annotations

import asyncio

from hyper.layouts.base import BaseLayout

from hyperdjango.actions import HTML, Signal, Toast, action


class PageView(BaseLayout):
    package_builds_started = 0

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

    @action
    async def retry_demo(self, request, **params):
        yield HTML(
            content="<div data-retry-first>First event delivered.</div>",
            target="#stream-log",
            swap="inner",
        )

        if not request.headers.get("Last-Event-ID"):
            raise ConnectionResetError("Intentional browser-test stream interruption")

        yield HTML(
            content="<div data-retry-resumed>Stream resumed.</div>",
            target="#stream-log",
            swap="append",
        )

    @action(method="POST", retry=False)
    def start_package_build(self, request, package_id="demo", **params):
        type(self).package_builds_started += 1
        job_id = f"{package_id}-{type(self).package_builds_started}"
        return self.watch_package_build.switch_to(job_id=job_id)

    @action(method="GET", retry=True)
    async def watch_package_build(self, request, job_id, **params):
        yield HTML(
            content=(
                f'<div data-build-first data-job-id="{job_id}">Watcher connected.</div>'
            ),
            target="#package-build-status",
            swap="inner",
        )
        if not request.headers.get("Last-Event-ID"):
            raise ConnectionResetError("Intentional switched-watcher interruption")
        yield HTML(
            content=(
                f'<div data-build-resumed data-mutation-count="{type(self).package_builds_started}">'
                "Watcher resumed.</div>"
            ),
            target="#package-build-status",
            swap="append",
        )
