from hyperdjango.actions import Signal, action

from hyper.layouts.base import BaseLayout


class PageView(BaseLayout):
    def get(self, request, slug, **params):
        return {
            "slug": slug,
            "title_text": slug.replace("-", " ").title(),
        }

    @action
    def bookmark(self, request, slug, **params):
        return [Signal(name="bookmarks", value={slug: True})]
