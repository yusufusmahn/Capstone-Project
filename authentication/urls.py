from django.urls import path, include
from . import views

app_name = 'authentication'

urlpatterns = [
    # Authentication endpoints
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('change-password/', views.PasswordChangeView.as_view(), name='change_password'),
    # Password reset endpoints are disabled/removed for now
    # path('reset-password-request/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    # path('reset-password/', views.PasswordResetView.as_view(), name='password_reset'),
    
    # User management (Admin only)
    path('users/', views.user_list, name='user_list'),
    path('voters/', views.voter_list, name='voter_list'),
    # New paginated/searchable endpoint
    path('voters/search/', views.VoterListView.as_view(), name='voter_list_search'),
    path('voters/<str:voter_id>/', views.VoterDetailView.as_view(), name='voter_detail'),
    path('voters/<str:voter_id>/history/', views.voter_history, name='voter_history'),
    path('voters/<str:voter_id>/verify/', views.verify_voter_registration, name='verify_voter'),
    path('voters/<str:voter_id>/cancel/', views.cancel_voter_registration, name='cancel_voter'),
    path('create-admin/', views.create_admin, name='create_admin'),
    path('create-inec-official/', views.create_inec_official, name='create_inec_official'),
]