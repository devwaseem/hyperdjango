from django.urls import path

from hyperdjango.integrations.devtools import views


app_name = "hyperdjango_devtools"

urlpatterns = [
    path("history/", views.history, name="history"),
    path("requests/<str:request_id>/", views.detail, name="detail"),
    path("requests/<str:request_id>/client/", views.client_update, name="client"),
    path("requests/<str:request_id>/pin/", views.pin, name="pin"),
    path("controls/clear/", views.clear, name="clear"),
    path("controls/pause/", views.pause, name="pause"),
]
