import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import ValorantProfile, ValorantMatch

# Agrega tu API Key aquí (Pega el token completo que empieza con HDEV-...)
HENRIK_API_KEY = "HDEV-3ee1161a-c93b-4e5d-b0d5-7b0767efa1f0" 
HEADERS = {
    "Authorization": HENRIK_API_KEY
}

# 1. Endpoint para buscar o registrar el perfil de Valorant del usuario
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_valorant_profile(request):
    game_name = request.data.get('gameName')
    tag_line = request.data.get('tagLine')
    region = request.data.get('region', 'latam').lower()

    if not game_name or not tag_line:
        return Response({'error': 'Se requiere el gameName y el tagLine'}, status=400)

    # Consultamos a la API de HenrikDev
    url = f"https://api.henrikdev.xyz/valorant/v1/account/{game_name}/{tag_line}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return Response({'error': 'No se encontró el usuario de Valorant en Riot Games'}, status=404)

    data = response.json().get('data', {})
    puuid = data.get('puuid')

    # Guardamos o actualizamos el perfil en nuestra base de datos PostgreSQL
    profile, created = ValorantProfile.objects.update_or_create(
        user=request.user,
        defaults={
            'game_name': game_name,
            'tag_line': tag_line,
            'region': region,
            'puuid': puuid
        }
    )

    return Response({
        'message': 'Perfil de Valorant guardado con éxito',
        'gameName': profile.game_name,
        'tagLine': profile.tag_line,
        'region': profile.region,
        'puuid': profile.puuid
    })

# 2. Endpoint para obtener el historial de partidas y estadísticas de Valorant
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_valorant_stats(request):
    try:
        profile = request.user.valorant_profile
    except ValorantProfile.DoesNotExist:
        return Response({'error': 'El usuario no tiene configurado un perfil de Valorant'}, status=404)

    # Consultamos las últimas partidas del usuario
    matches_url = f"https://api.henrikdev.xyz/valorant/v3/by-puuid/matches/{profile.region}/{profile.puuid}?size=5"
    matches_response = requests.get(matches_url, headers=HEADERS)

    if matches_response.status_code != 200:
        return Response({'error': 'No se pudieron obtener las partidas de Valorant'}, status=500)

    matches_data = matches_response.json().get('data', [])
    formatted_matches = []

    for match in matches_data:
        match_info = match.get('metadata', {})
        match_id = match_info.get('matchid')
        map_name = match_info.get('map', 'Desconocido')
        game_mode = match_info.get('mode', 'Competitivo')

        players = match.get('players', {}).get('all_players', [])
        player_stats = next((p for p in players if p.get('puuid') == profile.puuid), {})

        stats = player_stats.get('stats', {})
        kills = stats.get('kills', 0)
        deaths = stats.get('deaths', 0)
        assists = stats.get('assists', 0)
        agent_name = player_stats.get('character', 'Desconocido')
        
        team_id = player_stats.get('team') # 'Blue' o 'Red'
        teams = match.get('teams', {})
        team_data = teams.get(team_id.lower(), {}) if isinstance(teams, dict) else {}
        won = team_data.get('won', False)

        formatted_matches.append({
            'matchId': match_id,
            'mapName': map_name,
            'gameMode': game_mode,
            'agentName': agent_name,
            'kills': kills,
            'deaths': deaths,
            'assists': assists,
            'won': won
        })

    return Response({
        'profile': {
            'gameName': profile.game_name,
            'tagLine': profile.tag_line,
            'region': profile.region
        },
        'matches': formatted_matches
    })