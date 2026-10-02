import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# Pega aquí tu API Key de HenrikDev (la que empieza con HDEV-...)
HENRIK_API_KEY = "HDEV-3ee1161a-c93b-4e5d-b0d5-7b0767efa1f0" 
HEADERS = {
    "Authorization": HENRIK_API_KEY
}

@api_view(['GET'])
@permission_classes([AllowAny])  # Esto permite que cualquiera pueda buscar sin iniciar sesión
def search_valorant_profile(request, region, game_name, tag_line):
    # 1. Buscamos la cuenta para obtener el PUUID
    account_url = f"https://api.henrikdev.xyz/valorant/v1/account/{game_name}/{tag_line}"
    account_resp = requests.get(account_url, headers=HEADERS)

    if account_resp.status_code != 200:
        return Response({'error': 'No se encontró el jugador en Riot Games.'}, status=404)

    account_data = account_resp.json().get('data', {})
    puuid = account_data.get('puuid')
    
    # 2. Buscamos las últimas 5 partidas usando el PUUID y la región
    matches_url = f"https://api.henrikdev.xyz/valorant/v3/by-puuid/matches/{region}/{puuid}?size=5"
    matches_resp = requests.get(matches_url, headers=HEADERS)

    formatted_matches = []
    if matches_resp.status_code == 200:
        matches_data = matches_resp.json().get('data', [])
        for match in matches_data:
            match_info = match.get('metadata', {})
            match_id = match_info.get('matchid')
            map_name = match_info.get('map', 'Desconocido')
            game_mode = match_info.get('mode', 'Competitivo')

            players = match.get('players', {}).get('all_players', [])
            player_stats = next((p for p in players if p.get('puuid') == puuid), {})

            stats = player_stats.get('stats', {})
            kills = stats.get('kills', 0)
            deaths = stats.get('deaths', 0)
            assists = stats.get('assists', 0)
            agent_name = player_stats.get('character', 'Desconocido')

            team_id = player_stats.get('team')
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

    # 3. Devolvemos todo junto al frontend
    return Response({
        'profile': {
            'gameName': account_data.get('name'),
            'tagLine': account_data.get('tag'),
            'region': region.upper()
        },
        'matches': formatted_matches
    })