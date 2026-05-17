from django.urls import include, path
from . import views

urlpatterns = [
    path('trigger-agent/', views.trigger_agent),
    path("api/", include("agent_api.urls")),
]
