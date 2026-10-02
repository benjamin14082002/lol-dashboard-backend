# api/urls.py
from django.urls import path
from .views import get_summoner_profile, register_user, login_user

urlpatterns = [
    path('profile/<str:region>/<str:summoner_name>/', get_summoner_profile),
    path('auth/register/', register_user),
    path('auth/login/', login_user),
]