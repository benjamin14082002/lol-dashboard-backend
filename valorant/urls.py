from django.urls import path
from .views import save_valorant_profile, get_valorant_stats

urlpatterns = [
    path('profile/', save_valorant_profile, name='save_valorant_profile'),
    path('stats/', get_valorant_stats, name='get_valorant_stats'),
]