from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class ValorantProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='valorant_profile')
    game_name = models.CharField(max_length=50) # El nombre del Riot ID (ej: "Flippy")
    tag_line = models.CharField(max_length=10)   # El tag (ej: "LAS" o "NA1")
    region = models.CharField(max_length=10, default='latam')
    puuid = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.game_name}#{self.tag_line}"

class ValorantMatch(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='valorant_matches')
    match_id = models.CharField(max_length=100, unique=True)
    agent_name = models.CharField(max_length=50)
    map_name = models.CharField(max_length=50)
    game_mode = models.CharField(max_length=50)
    won = models.BooleanField(default=False)
    kills = models.IntegerField(default=0)
    deaths = models.IntegerField(default=0)
    assists = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.match_id} - {self.agent_name} ({'Win' if self.won else 'Loss'})"