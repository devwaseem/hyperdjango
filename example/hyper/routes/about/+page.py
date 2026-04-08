from hyper.layouts.base import BaseLayout


class PageView(BaseLayout):
    def get(self, request, **params):
        return {
            "title_text": "About this example",
            "content": "This is a static route from hyper/routes/about/+page.py",
        }
