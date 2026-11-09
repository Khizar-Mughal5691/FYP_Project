from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/api/", permanent=False)),   # the bare address opens the API index
    path("api/", include("api.urls")),
]
