from __future__ import annotations

from hyper.layouts.base import BaseLayout

from hyperdjango.actions import HTML, Toast, action


class PageView(BaseLayout):
    def get(self, request, **params):
        return {}

    @action
    def upload_demo_alpine(self, request, **params):
        return self._upload_demo(request, target="#upload-result-alpine")

    @action
    def upload_demo_window(self, request, **params):
        return self._upload_demo(request, target="#upload-result-window")

    def _upload_demo(self, request, *, target: str):
        uploaded = request.FILES.get("upload")
        if uploaded is None:
            return [
                HTML(
                    content=self.render(
                        request=request,
                        relative_template_name="partials/result.html",
                        context_updates={
                            "error": "Choose a file before uploading.",
                            "uploaded_name": "",
                            "uploaded_size_kb": "",
                            "content_type": "",
                        },
                    ),
                    target=target,
                )
            ]

        return [
            Toast(
                payload={
                    "type": "success",
                    "title": "Uploaded",
                    "message": f"{uploaded.name} uploaded successfully.",
                }
            ),
            HTML(
                content=self.render(
                    request=request,
                    relative_template_name="partials/result.html",
                    context_updates={
                        "error": "",
                        "uploaded_name": uploaded.name,
                        "uploaded_size_kb": f"{uploaded.size / 1024:.1f}",
                        "content_type": uploaded.content_type or "unknown",
                    },
                ),
                target=target,
            ),
        ]
