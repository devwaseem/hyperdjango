from django.http import HttpResponse
from django.urls import path

from hyperdjango.urls import include_routes

from hyper.shared.docs_content import build_llms_markdown


def llms_txt_view(request):
    return HttpResponse(
        build_llms_markdown(),
        content_type="text/markdown; charset=utf-8",
    )


urlpatterns = [
    path("llms.txt", llms_txt_view),
    *include_routes(),
]
