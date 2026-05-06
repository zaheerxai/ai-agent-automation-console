from django.urls import include, path

urlpatterns = [
    path("api/", include("agent_api.urls")),
]
