from django.urls import path

from .views import trigger_agent

urlpatterns = [
    path("trigger-agent/", trigger_agent, name="trigger-agent"),
]
