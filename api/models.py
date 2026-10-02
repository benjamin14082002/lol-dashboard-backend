# api/models.py
from django.db import models

class SummonerProfile(models.Model):
    summoner_name = models.CharField(max_length=100)
    region = models.CharField(max_length=10)
    puuid = models.CharField(max_length=100, unique=True)
    winrate = models.CharField(max_length=10)
    kda = models.CharField(max_length=10)
    cs_per_min = models.CharField(max_length=10)
    
    ranked_solo = models.JSONField(null=True, blank=True)
    ranked_flex = models.JSONField(null=True, blank=True)
    
    profile_icon = models.IntegerField(default=1)
    summoner_level = models.IntegerField(default=1)
    
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.summoner_name} ({self.region})"

class Match(models.Model):
    summoner = models.ForeignKey(SummonerProfile, on_delete=models.CASCADE, related_name='matches')
    match_id = models.CharField(max_length=50)
    win = models.BooleanField()
    champion_name = models.CharField(max_length=50)
    kills = models.IntegerField()
    deaths = models.IntegerField()
    assists = models.IntegerField()
    duration = models.CharField(max_length=10)
    items = models.JSONField()
    participants_data = models.JSONField(default=list, null=True, blank=True)
    
    # NUEVOS CAMPOS: Hechizos y Runas
    spells = models.JSONField(default=list, null=True, blank=True)
    runes = models.JSONField(default=list, null=True, blank=True)

    def __str__(self):
        return f"{self.summoner.summoner_name} - {self.champion_name} - {self.match_id}"

from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    riot_id = models.CharField(max_length=100) # Ej: Benjamin#LAS
    region = models.CharField(max_length=10)     # Ej: LAS
    puuid = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.username} -> {self.riot_id}"