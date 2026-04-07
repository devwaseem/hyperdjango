from django.contrib import admin
from django.urls import path

from hyper.template_views import profile_card
from hyperdjango.urls import include_routes


urlpatterns = [
    path("admin/", admin.site.urls),
    path("template-card/", profile_card),
    *include_routes(),
]
