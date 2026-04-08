from __future__ import annotations

from django.shortcuts import render
from django.views import View


class PageView(View):
    def get(self, request, **params):
        return render(
            request,
            "routes/plain-django-view/index.html",
            {"same_request": request is self.request},
        )
