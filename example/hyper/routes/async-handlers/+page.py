from __future__ import annotations

import asyncio

from hyper.layouts.base import BaseLayout


class PageView(BaseLayout):
    async def get(self, request, **params):
        return {
            "headline": "Async GET and POST handlers",
            "saved_name": request.session.get("async_saved_name", ""),
            "request_method": "GET",
        }

    async def post(self, request, **params):
        await asyncio.sleep(0.05)
        saved_name = str(request.POST.get("name", "")).strip()
        request.session["async_saved_name"] = saved_name
        return {
            "headline": "Async GET and POST handlers",
            "saved_name": saved_name,
            "request_method": "POST",
        }
