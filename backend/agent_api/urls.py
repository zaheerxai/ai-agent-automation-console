from django.urls import path
from . import views  # This is the cleanest way to import multiple views

urlpatterns = [
    # Only define the path once. 
    # Using 'views.trigger_agent' matches your 'views' import above.
    path("trigger-agent/", views.trigger_agent, name="trigger-agent"),
    
    # Clerk Webhook
    path('webhooks/clerk/', views.clerk_webhook, name="clerk-webhook"),
]