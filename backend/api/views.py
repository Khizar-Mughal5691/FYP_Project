"""HTTP endpoints. Each view only reads the request and calls api/services.py."""
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api import services


def _respond(fn, *args):
    try:
        return Response(fn(*args))
    except services.NotFound as e:
        return Response({"error": str(e)}, status=404)
    except services.BadRequest as e:
        return Response({"error": str(e)}, status=400)


@api_view(["GET"])
def index(request):
    """Start here: every address of the API, as links."""
    base = request.build_absolute_uri("/api/")
    return Response(dict(
        name="Meta-Fut A.I API",
        endpoints=[
            dict(method="GET", url=base + "health/", purpose="Status and data credit"),
            dict(method="GET", url=base + "teams/", purpose="All 80 teams; add ?league=la_liga for one league"),
            dict(method="GET", url=base + "teams/barcelona/", purpose="One team's profile, usual eleven and squad"),
            dict(method="GET", url=base + "players/5503/", purpose="One player's profile (5503 is Lionel Messi)"),
            dict(method="POST", url=base + "simulations/",
                 purpose='Simulate a fixture. Body: {"home": "barcelona", "away": "real-madrid", "rollouts": 200}'),
        ],
        documentation="docs/api.md in the project folder",
        credit=services.DATA_CREDIT))


@api_view(["GET"])
def health(request):
    """Is the API up, and which model and data does it use."""
    return _respond(services.health)


@api_view(["GET"])
def teams(request):
    """All 80 teams, or one league's: ?league=la_liga"""
    return _respond(services.team_list, request.query_params.get("league"))


@api_view(["GET"])
def team(request, team_id):
    """One team: its profile numbers, usual eleven and squad."""
    return _respond(services.team_detail, team_id)


@api_view(["GET"])
def player(request, player_id):
    """One player: action shares, involvement and touch map."""
    return _respond(services.player_detail, player_id)


@api_view(["POST"])
def simulations(request):
    """Simulate a fixture. Body: {"home": "barcelona", "away": "real-madrid", "rollouts": 200}"""
    return _respond(services.simulate_request, request.data)
