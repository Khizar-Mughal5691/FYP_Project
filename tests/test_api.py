"""Tests for the REST API. They need trained models, so they skip on a fresh checkout."""
import json
import os

import pytest

from metafut.config import BUNDLE, MODEL_DIR

pytestmark = pytest.mark.skipif(not (MODEL_DIR / BUNDLE).exists(), reason="run scripts/03_train_models.py first")


@pytest.fixture(scope="module")
def client():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "metafut_api.settings")
    import django
    django.setup()
    from django.test import Client
    return Client()


def get(client, url):
    r = client.get(url, HTTP_ACCEPT="application/json")
    return r.status_code, r.json()


def post(client, body):
    r = client.post("/api/simulations/", data=json.dumps(body), content_type="application/json")
    return r.status_code, r.json()


def test_bare_address_leads_to_the_api_index(client):
    r = client.get("/")
    assert r.status_code == 302 and r["Location"] == "/api/"
    status, body = get(client, "/api/")
    assert status == 200 and len(body["endpoints"]) == 5
    assert all(e["url"].startswith("http://testserver/api/") for e in body["endpoints"])


def test_health(client):
    status, body = get(client, "/api/health/")
    assert status == 200 and body["status"] == "ok"
    assert body["teams"] == 80 and len(body["leagues"]) == 4


def test_team_list_and_league_filter(client):
    status, teams = get(client, "/api/teams/")
    assert status == 200 and len(teams) == 80
    assert len({t["id"] for t in teams}) == 80
    status, la_liga = get(client, "/api/teams/?league=la_liga")
    assert len(la_liga) == 20 and {t["league"] for t in la_liga} == {"la_liga"}
    assert get(client, "/api/teams/?league=mls")[0] == 400


def test_team_detail_by_id_or_by_name(client):
    status, team = get(client, "/api/teams/atletico-madrid/")
    assert status == 200 and team["name"] == "Atlético Madrid"
    assert get(client, "/api/teams/Atletico%20Madrid/")[1]["id"] == "atletico-madrid"
    assert len(team["profile"]) == 8
    assert all(1 <= p["rank"] <= p["out_of"] == 80 for p in team["profile"])
    assert len(team["usual_xi"]) == 11
    assert sum(p["position"] == "GK" for p in team["usual_xi"]) == 1
    assert len(team["squad"]) >= 11


def test_unknown_team_suggests_names(client):
    status, body = get(client, "/api/teams/madrid/")
    assert status == 404
    assert "Real Madrid" in body["error"] and "Atlético Madrid" in body["error"]


def test_player_detail(client):
    squad = get(client, "/api/teams/barcelona/")[1]["squad"]
    status, player = get(client, f"/api/players/{squad[0]['player_id']}/")
    assert status == 200
    assert abs(sum(a["share"] for a in player["actions"]) - 1) < 1e-3
    assert len(player["touch_map"]["values"]) == player["touch_map"]["columns"] * player["touch_map"]["rows"]
    assert player["teams"][0]["id"] == "barcelona"
    assert get(client, "/api/players/1/")[0] == 404


def test_simulation(client):
    status, sim = post(client, {"home": "barcelona", "away": "real-madrid", "rollouts": 10, "seed": 3,
                                "include_events": True})
    assert status == 200
    p = sim["probabilities"]
    assert abs(p["home_win"] + p["draw"] + p["away_win"] - 1) < 1e-6
    sample = sim["sample_match"]
    assert len(sample["goals"]) == sample["score"]["home"] + sample["score"]["away"]
    assert len(sample["events"]) > 1000
    assert len(sim["lineups"]["home"]) == len(sim["lineups"]["away"]) == 11
    assert 0 < len(sim["likely_scorers"]) <= 5
    # The same seed gives the same simulation.
    assert post(client, {"home": "barcelona", "away": "real-madrid", "rollouts": 10, "seed": 3})[1]["probabilities"] == p


def test_custom_eleven(client):
    xi = get(client, "/api/teams/levante-ud/")[1]["usual_xi"]
    body = {"home": "levante-ud", "away": "barcelona", "rollouts": 5, "seed": 1,
            "home_xi": [{"player_id": x["player_id"], "position": x["position"]} for x in xi]}
    assert post(client, body)[0] == 200
    body["home_xi"] = body["home_xi"][:10]
    status, error = post(client, body)
    assert status == 400 and "11" in error["error"]


@pytest.mark.parametrize("body, words", [
    ({"home": "barcelona", "away": "barcelona"}, "different"),
    ({"home": "barcelona", "away": "real-madrid", "rollouts": 0}, "rollouts"),
    ({"home": "barcelona", "away": "real-madrid", "rollouts": "many"}, "rollouts"),
    ({"home": "barcelona"}, "missing"),
    ({"home": "barcelona", "away": "real-madrid", "colour": "red"}, "unknown field"),
    ({"home": "barcelona", "away": "nowhere"}, "unknown team"),
])
def test_simulation_rejects_bad_requests(client, body, words):
    status, error = post(client, body)
    assert status in (400, 404) and words in error["error"]


def test_simulations_only_accepts_post(client):
    assert client.get("/api/simulations/", HTTP_ACCEPT="application/json").status_code == 405
