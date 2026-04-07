from django.contrib import admin
from django.urls import path

from hyperdjango.urls import include_routes


urlpatterns = [
    path("admin/", admin.site.urls),
    *include_routes(),
]
