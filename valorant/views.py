import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

HENRIK_API_KEY = "HDEV-3ee1161a-c93b-4e5d-b0d5-7b0767efa1f0" 
HEADERS = {
    "Authorization": HENRIK_API_KEY
}

@api_view(['GET'])
@permission_classes([AllowAny])
def search_valorant_profile(request, region, game_name, tag_line):
    # 1. Buscamos la cuenta
    account_url = f"https://api.henrikdev.xyz/valorant/v1/account/{game_name}/{tag_line}"
    account_resp = requests.get(account_url, headers=HEADERS)

    if account_resp.status_code != 200:
        return Response({'error': f'Error al buscar jugador. Código API: {account_resp.status_code}'}, status=404)

    # Usamos "or {}" para evitar crasheos si la API devuelve null en 'data'
    account_data = account_resp.json().get('data') or {}
    puuid = account_data.get('puuid')
    account_level = account_data.get('account_level', 0)
    player_card = (account_data.get('card') or {}).get('small', '')

    # 2. Buscamos el Rango Competitivo
    mmr_url = f"https://api.henrikdev.xyz/valorant/v1/mmr/{region}/{game_name}/{tag_line}"
    mmr_resp = requests.get(mmr_url, headers=HEADERS)
    
    rank_name = "Unranked"
    rank_image = ""
    if mmr_resp.status_code == 200:
        mmr_data = mmr_resp.json().get('data') or {}
        rank_name = mmr_data.get('currenttierpatched', 'Unranked')
        rank_image = (mmr_data.get('images') or {}).get('small', '')

    # 3. Buscamos las últimas 10 partidas
    matches_url = f"https://api.henrikdev.xyz/valorant/v3/by-puuid/matches/{region}/{puuid}?size=10"
    matches_resp = requests.get(matches_url, headers=HEADERS)

    if matches_resp.status_code != 200:
        return Response({'error': f'Riot denegó el historial. Código API: {matches_resp.status_code}'}, status=404)

    formatted_matches = []
    matches_data = matches_resp.json().get('data') or []
    
    for match in matches_data:
        try:
            # Envolvemos cada partida en un try-except. Si falla una, no crashea todo el sistema.
            match_info = match.get('metadata') or {}
            match_id = match_info.get('matchid')
            map_name = match_info.get('map', 'Desconocido')
            game_mode = match_info.get('mode', 'Desconocido')
            game_start = match_info.get('game_start', 0)

            players_dict = match.get('players') or {}
            players = players_dict.get('all_players') or []
            
            all_players_data = []
            for p in players:
                p_stats = p.get('stats') or {}
                all_players_data.append({
                    'puuid': p.get('puuid'),
                    'name': p.get('name', 'Desconocido'),
                    'tag': p.get('tag', ''),
                    'team': p.get('team', 'Unknown'),
                    'agent': p.get('character', 'Desconocido'),
                    'kills': p_stats.get('kills', 0),
                    'deaths': p_stats.get('deaths', 0),
                    'assists': p_stats.get('assists', 0)
                })

            player_stats = next((p for p in players if p.get('puuid') == puuid), {})
            stats = player_stats.get('stats') or {}
            kills = stats.get('kills', 0)
            deaths = stats.get('deaths', 0)
            assists = stats.get('assists', 0)
            agent_name = player_stats.get('character', 'Desconocido')

            team_id = player_stats.get('team')
            teams = match.get('teams') or {}
            
            won = False
            # Verificación ultra segura para evitar errores AttributeError con strings nulos
            if team_id and isinstance(team_id, str) and isinstance(teams, dict):
                team_data = teams.get(team_id.lower()) or {}
                won = team_data.get('won', False)

            formatted_matches.append({
                'matchId': match_id,
                'mapName': map_name,
                'gameMode': game_mode,
                'agentName': agent_name,
                'kills': kills,
                'deaths': deaths,
                'assists': assists,
                'won': won,
                'allPlayers': all_players_data,
                'gameStart': game_start
            })
        except Exception as e:
            # Si una partida da error (ej. Deathmatch vacío), la ignoramos y pasamos a la siguiente
            print(f"Partida {match.get('metadata', {}).get('matchid')} ignorada por error de formato: {e}")
            continue

    return Response({
        'profile': {
            'gameName': account_data.get('name'),
            'tagLine': account_data.get('tag'),
            'region': region.upper(),
            'level': account_level,
            'cardImage': player_card,
            'rankName': rank_name,
            'rankImage': rank_image
        },
        'matches': formatted_matches
    })