from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'incidents'

router = DefaultRouter()
router.register(r'reports', views.IncidentReportViewSet)

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    
    # Incident management
    path('assign/', views.assign_incident, name='assign_incident'),
    path('reports/<uuid:incident_id>/status/', views.update_incident_status, name='update_incident_status'),
    path('response/', views.add_incident_response, name='add_incident_response'),
    path('my-incidents/', views.my_incidents, name='my_incidents'),
    
    # Statistics
    path('stats/', views.incident_stats, name='incident_stats'),
]