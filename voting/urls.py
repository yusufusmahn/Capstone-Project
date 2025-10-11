from django.urls import path
from . import views

app_name = 'voting'

urlpatterns = [
    # Voting endpoints
    path('cast-vote/', views.CastVoteView.as_view(), name='cast_vote'),
    path('ballot/<uuid:election_id>/', views.get_ballot, name='get_ballot'),
    path('history/', views.voting_history, name='voting_history'),
    path('verify/', views.verify_vote, name='verify_vote'),
    
    # Voting sessions
    path('session/start/', views.start_voting_session, name='start_voting_session'),
    
    # Statistics
    path('stats/', views.voting_stats, name='voting_stats'),
]