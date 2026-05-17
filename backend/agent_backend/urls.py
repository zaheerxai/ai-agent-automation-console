from django.urls import path, include

urlpatterns = [
    path('api/', include('agent_api.urls')), # Points to the app
]
