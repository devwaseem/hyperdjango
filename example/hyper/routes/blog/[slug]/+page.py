from hyperdjango.actions import action

from hyper.layouts.base import BaseLayout


class PageView(BaseLayout):
    def get(self, request, slug, **params):
        return {
            "slug": slug,
            "title_text": slug.replace("-", " ").title(),
        }

    @action
    def bookmark(self, request, slug, **params):
        return self.action_response(
            signals={
                "bookmarks": {
                    slug: True,
                }
            }
        )
