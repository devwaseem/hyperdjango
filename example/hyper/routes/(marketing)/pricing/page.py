from hyper.layouts.base import BaseLayout


class PageView(BaseLayout):
    def get(self, request, **params):
        return {
            "plans": [
                {"name": "Starter", "price": "$0"},
                {"name": "Pro", "price": "$19"},
                {"name": "Scale", "price": "$99"},
            ]
        }
