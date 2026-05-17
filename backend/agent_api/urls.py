from django.urls import path

from .views import trigger_agent

urlpatterns = [
    path("trigger-agent/", trigger_agent, name="trigger-agent"),
    path('trigger-agent/', views.trigger_agent),
    path('webhooks/clerk/', views.clerk_webhook), # Point Clerk Dashboard here
]
