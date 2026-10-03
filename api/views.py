# api/views.py
from rest_framework.response import Response
from rest_framework.decorators import api_view
import requests
from django.utils import timezone
from datetime import timedelta
from .models import SummonerProfile, Match

RIOT_API_KEY = "RGAPI-969bcd22-886a-4ccb-8dac-2a28d9b21eab"

REGION_MAPPING = {
    "LAS": "la2", "LAN": "la1", "NA": "na1", 
    "EUW": "euw1", "EUNE": "eun1", "BR": "br1"
}

QUEUE_MAPPING = {
    420: "Ranked Solo",
    440: "Ranked Flex",
    400: "Normal Draft",
    430: "Normal Blind",
    450: "ARAM",
    700: "Clash",
    1900: "URF"
}

@api_view(['GET'])
def get_summoner_profile(request, region, summoner_name):
    if "#" in summoner_name:
        game_name, tag_line = summoner_name.split("#", 1)
    else:
        game_name = summoner_name
        tag_line = region 
        
    headers = {"X-Riot-Token": RIOT_API_KEY}
    plat_region = REGION_MAPPING.get(region.upper(), "la2")
    
    account_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    acc_res = requests.get(account_url, headers=headers)
    
    if acc_res.status_code != 200:
        return Response({"status": "error", "message": f"Invocador no encontrado. Error: {acc_res.text}"}, status=acc_res.status_code)
        
    account_data = acc_res.json()
    puuid = account_data.get('puuid')
    real_name = f"{account_data.get('gameName')}#{account_data.get('tagLine')}"

    # Extraemos el verdadero campeón principal y su maestría
    mastery_url = f"https://{plat_region}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count=1"
    mastery_res = requests.get(mastery_url, headers=headers)
    
    true_main_id = 0
    champion_level = 0
    champion_points = 0
    
    if mastery_res.status_code == 200 and mastery_res.json():
        top_champ = mastery_res.json()[0]
        true_main_id = top_champ.get('championId', 0)
        champion_level = top_champ.get('championLevel', 0)
        champion_points = top_champ.get('championPoints', 0)

    try:
        profile = SummonerProfile.objects.get(puuid=puuid)
        if timezone.now() - profile.last_updated < timedelta(minutes=15):
            db_matches = profile.matches.all()
            real_matches = [{
                "id": m.match_id, "win": m.win, "championName": m.champion_name, 
                "kills": m.kills, "deaths": m.deaths, "assists": m.assists, 
                "duration": m.duration, "date": "Reciente", "items": m.items,
                "participants_data": m.participants_data,
                "spells": m.spells, "runes": m.runes
            } for m in db_matches]
            
            return Response({
                "summoner": profile.summoner_name, "region": profile.region,
                "profileIcon": profile.profile_icon, "summonerLevel": profile.summoner_level,
                "status": "success", "message": "⚡ ¡Datos cargados desde la Base de Datos!",
                "rankedSolo": profile.ranked_solo, "rankedFlex": profile.ranked_flex,
                "stats": {"winrate": profile.winrate, "kda": profile.kda, "csPerMin": profile.cs_per_min},
                "matches": real_matches,
                "trueMainId": true_main_id,
                "championLevel": champion_level,
                "championPoints": champion_points
            })
    except SummonerProfile.DoesNotExist:
        pass

    summ_url = f"https://{plat_region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    summ_res = requests.get(summ_url, headers=headers)
    
    profile_icon, summoner_level = 1, 1
    if summ_res.status_code == 200:
        summ_data = summ_res.json()
        profile_icon = summ_data.get('profileIconId', 1)
        summoner_level = summ_data.get('summonerLevel', 1)

    ranked_solo, ranked_flex = None, None
    league_url = f"https://{plat_region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    league_res = requests.get(league_url, headers=headers)
    
    if league_res.status_code == 200:
        for l in league_res.json():
            data = {"tier": l['tier'], "rank": l['rank'], "lp": l['leaguePoints'], "wins": l['wins'], "losses": l['losses']}
            if l.get('queueType') == 'RANKED_SOLO_5x5': ranked_solo = data
            elif l.get('queueType') == 'RANKED_FLEX_SR': ranked_flex = data

    matches_url = f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=10"
    matches_res = requests.get(matches_url, headers=headers)
    
    if matches_res.status_code != 200:
        return Response({"status": "error", "message": "Error al obtener historial"}, status=matches_res.status_code)
        
    match_ids = matches_res.json()
    real_matches = []
    t_kills, t_deaths, t_assists, wins, t_cs, t_mins = 0, 0, 0, 0, 0, 0

    for m_id in match_ids:
        detail_res = requests.get(f"https://americas.api.riotgames.com/lol/match/v5/matches/{m_id}", headers=headers)
        
        if detail_res.status_code == 200:
            match_data = detail_res.json()
            info = match_data.get('info', {})
            participants = info.get('participants', [])
            
            queue_id = info.get('queueId', 0)
            game_mode = QUEUE_MAPPING.get(queue_id, "Partida")
            
            all_participants = [{
                "summonerName": p.get("riotIdGameName") or p.get("summonerName") or "Unknown", 
                "championName": p.get("championName"), "teamId": p.get("teamId"), 
                "kills": p.get("kills", 0), "deaths": p.get("deaths", 0), "assists": p.get("assists", 0),
                "multikill": p.get("largestMultiKill", 0)
            } for p in participants]
            
            player = next((p for p in participants if p.get('puuid') == puuid), None)
            
            if player:
                t_kills += player.get('kills', 0)
                t_deaths += player.get('deaths', 0)
                t_assists += player.get('assists', 0)
                if player.get('win'): wins += 1
                
                cs = player.get('totalMinionsKilled', 0) + player.get('neutralMinionsKilled', 0)
                dur_seg = info.get('gameDuration', 0)
                dur_min = dur_seg / 60 if dur_seg > 0 else 1
                
                t_cs += cs
                t_mins += dur_min

                spells = [player.get('summoner1Id', 0), player.get('summoner2Id', 0)]
                runes = [0, 0]
                try:
                    styles = player.get('perks', {}).get('styles', [])
                    if len(styles) > 0:
                        runes[0] = styles[0]['selections'][0]['perk']
                    if len(styles) > 1:
                        runes[1] = styles[1]['style']
                except Exception:
                    pass

                real_matches.append({
                    "id": m_id, 
                    "win": player.get('win', False), 
                    "gameMode": game_mode, 
                    "queueId": queue_id,   
                    "championName": player.get('championName', 'Unknown'), 
                    "kills": player.get('kills', 0), "deaths": player.get('deaths', 0), "assists": player.get('assists', 0),
                    "duration": f"{int(dur_min)}:{int(dur_seg % 60):02d}", "date": "Reciente",
                    "items": [player.get(f'item{i}', 0) for i in range(7)],
                    "participants_data": all_participants,
                    "spells": spells, "runes": runes
                })

    total_games = len(real_matches)
    winrate = f"{int((wins / total_games) * 100)}%" if total_games > 0 else "0%"
    kda_ratio = str(round((t_kills + t_assists) / max(1, t_deaths), 2))
    cs_per_min = str(round(t_cs / max(1, t_mins), 1))

    profile, _ = SummonerProfile.objects.update_or_create(
        puuid=puuid, defaults={'summoner_name': real_name, 'region': region, 'winrate': winrate, 'kda': kda_ratio, 'cs_per_min': cs_per_min, 'ranked_solo': ranked_solo, 'ranked_flex': ranked_flex, 'profile_icon': profile_icon, 'summoner_level': summoner_level}
    )

    profile.matches.all().delete()
    for m in real_matches:
        Match.objects.create(
            summoner=profile, match_id=m['id'], win=m['win'], champion_name=m['championName'], kills=m['kills'], deaths=m['deaths'], assists=m['assists'], duration=m['duration'], items=m['items'], participants_data=m['participants_data'], spells=m['spells'], runes=m['runes']
        )

    return Response({
        "summoner": real_name, "region": region, "profileIcon": profile_icon, "summonerLevel": summoner_level,
        "status": "success", "message": "🚀 ¡Datos actualizados!",
        "rankedSolo": ranked_solo, "rankedFlex": ranked_flex,
        "stats": {"winrate": winrate, "kda": kda_ratio, "csPerMin": cs_per_min}, 
        "matches": real_matches,
        "trueMainId": true_main_id,
        "championLevel": champion_level,
        "championPoints": champion_points
    })

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import UserProfile

@api_view(['POST'])
def register_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    riot_id = request.data.get('riot_id')
    region = request.data.get('region', 'LAS')

    if not username or not password or not riot_id:
        return Response({"status": "error", "message": "Faltan campos obligatorios."}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({"status": "error", "message": "El nombre de usuario ya está en uso."}, status=400)

    if "#" in riot_id:
        game_name, tag_line = riot_id.split("#", 1)
    else:
        game_name = riot_id
        tag_line = region

    headers = {"X-Riot-Token": RIOT_API_KEY}
    account_url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    acc_res = requests.get(account_url, headers=headers)

    if acc_res.status_code != 200:
        return Response({"status": "error", "message": "❌ El Riot ID ingresado no existe."}, status=400)

    account_data = acc_res.json()
    puuid = account_data.get('puuid')
    real_riot_id = f"{account_data.get('gameName')}#{account_data.get('tagLine')}"

    user = User.objects.create_user(username=username, password=password)
    UserProfile.objects.create(user=user, riot_id=real_riot_id, region=region, puuid=puuid)

    return Response({
        "status": "success", 
        "message": "¡Cuenta creada con éxito!",
        "riot_id": real_riot_id
    })

@api_view(['POST'])
def login_user(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)
    if user is not None:
        try:
            profile = user.profile
            return Response({
                "status": "success",
                "username": user.username,
                "riot_id": profile.riot_id,
                "region": profile.region
            })
        except UserProfile.DoesNotExist:
            return Response({"status": "error", "message": "El usuario no tiene un perfil asociado."}, status=400)
    
    return Response({"status": "error", "message": "Usuario o contraseña incorrectos."}, status=400)