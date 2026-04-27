from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.http import HttpResponse
from django.urls import path

from config.views import page_not_found, robots_txt, server_error, sitemap_xml
from hyper.shared.docs_content import build_llms_markdown
from hyperdjango.urls import include_routes


def llms_txt_view(_request):
    return HttpResponse(
        build_llms_markdown(), content_type="text/markdown; charset=utf-8"
    )


urlpatterns = [
    path("robots.txt", robots_txt),
    path("sitemap.xml", sitemap_xml),
    path("llms.txt", llms_txt_view),
    *include_routes(),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

handler404 = page_not_found
handler500 = server_error
