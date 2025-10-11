from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'elections'

router = DefaultRouter()
router.register(r'elections', views.ElectionViewSet)
router.register(r'candidates', views.CandidateViewSet)

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    
    # Election management
    path('elections/<uuid:election_id>/results/', views.election_results, name='election_results'),
    path('elections/<uuid:election_id>/live-results/', views.live_election_results, name='live_election_results'),
    path('elections/<uuid:election_id>/start/', views.start_election, name='start_election'),
    path('elections/<uuid:election_id>/end/', views.end_election, name='end_election'),
    path('elections/check-status/', views.check_election_status, name='check_election_status'),
    path('active/', views.active_elections, name='active_elections'),
]