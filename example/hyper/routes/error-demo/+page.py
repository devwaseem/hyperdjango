from __future__ import annotations

from django.core.exceptions import PermissionDenied

from hyper.layouts.base import BaseLayout

from hyperdjango.actions import action


class PageView(BaseLayout):
    def get(self, request, **params):
        return {}

    @action
    def forbidden(self, request, **params):
        raise PermissionDenied("Only staff can perform this action.")
