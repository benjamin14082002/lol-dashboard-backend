from django.urls import path
from .views import search_valorant_profile

urlpatterns = [
    # Nueva ruta pública para buscar cuentas (reemplaza a profile/ y stats/)
    path('search/<str:region>/<str:game_name>/<str:tag_line>/', search_valorant_profile, name='search_valorant_profile'),
]