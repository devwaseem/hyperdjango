from __future__ import annotations

from hyper.layouts.base import BaseLayout

from hyperdjango.actions import action


class PageView(BaseLayout):
    def get(self, request, **params):
        return {}

    @action
    def upload_demo(self, request, **params):
        uploaded = request.FILES.get("upload")
        if uploaded is None:
            return self.action_response(
                html=self.render(
                    request=request,
                    relative_template_name="partials/result.html",
                    context_updates={
                        "error": "Choose a file before uploading.",
                        "uploaded_name": "",
                        "uploaded_size_kb": "",
                        "content_type": "",
                    },
                ),
                status=400,
            )

        return self.action_response(
            html=self.render(
                request=request,
                relative_template_name="partials/result.html",
                context_updates={
                    "error": "",
                    "uploaded_name": uploaded.name,
                    "uploaded_size_kb": f"{uploaded.size / 1024:.1f}",
                    "content_type": uploaded.content_type or "unknown",
                },
            ),
            toast={
                "type": "success",
                "title": "Uploaded",
                "message": f"{uploaded.name} uploaded successfully.",
            },
        )
