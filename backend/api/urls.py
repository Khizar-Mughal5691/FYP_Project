from django.urls import path

from api import views

urlpatterns = [
    path("", views.index, name="index"),
    path("health/", views.health, name="health"),
    path("teams/", views.teams, name="teams"),
    path("teams/<str:team_id>/", views.team, name="team"),
    path("players/", views.players, name="players"),
    path("players/<int:player_id>/", views.player, name="player"),
    path("simulations/", views.simulations, name="simulations"),
]
