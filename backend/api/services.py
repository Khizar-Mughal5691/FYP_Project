"""The two Phase-I features as plain functions that the API views call.

1. Player behavioural modelling: team and player profiles learned from real matches.
2. Event-driven match simulation: two real teams and their elevens, simulated many times.

Nothing here depends on Django, so these functions can be tested and reused on their own.
Profiles and models come from the trained bundle; names, leagues and squads come from the
training matches, the same matches the profiles were learned from.
"""
import re
import time
import unicodedata
from functools import lru_cache

import numpy as np
import pandas as pd

from metafut.config import ACTIONS, BUNDLE, LEAGUES, POSITION_ID, POSITIONS, RESULTS, TABLE_DIR
from metafut.models.features import TEAM_ATT, TEAM_DEF
from metafut.models.profiles import STYLE_X, STYLE_Y
from metafut.sim import fixtures as fixture_tools
from metafut.sim.engine import Simulator, player_name

DEFAULT_ROLLOUTS = 200
MAX_ROLLOUTS = 1000
TOP_SCORELINES = 10
TOP_SCORERS = 5
DATA_CREDIT = "Data: StatsBomb open data, 2015/16 season, used for non-commercial research."
LEAGUE_NAMES = {key: name for key, (name, _) in LEAGUES.items()}

# Profile number -> (label, whether a higher or lower value is better for the team).
TEAM_NUMBERS = {
    "att_pass": ("Pass completion", "higher"),
    "att_shot": ("Shots, as a share of the team's decisions", "higher"),
    "att_loss": ("Ball losses, as a share of the team's decisions", "lower"),
    "def_pass": ("Opponents' pass completion", "lower"),
    "def_shot": ("Opponents' shots, as a share of their decisions", "lower"),
    "def_loss": ("Ball losses forced, as a share of opponents' decisions", "higher"),
    "def_press": ("Opponents' open-play decisions under pressure", "higher"),
    "press_factor": ("Pressing compared with what the situation predicts (1 = average)", "higher"),
}


class NotFound(Exception):
    pass


class BadRequest(Exception):
    pass


def slugify(name):
    text = unicodedata.normalize("NFKD", name)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


@lru_cache(maxsize=1)
def simulator():
    return Simulator()


@lru_cache(maxsize=1)
def catalog():
    """Names, leagues, squads and appearance counts, loaded once per server process."""
    profiles = simulator().profiles
    matches = pd.read_parquet(TABLE_DIR / "matches.parquet")
    lineups = pd.read_parquet(TABLE_DIR / "lineups.parquet")
    train_ids = matches.loc[matches.split == "train", "match_id"]
    decisions = pd.read_parquet(TABLE_DIR / "decisions.parquet", columns=["match_id", "team", "player_id", "split"])
    decisions = decisions[decisions.split == "train"]

    league = pd.concat([matches[["home", "league"]].set_axis(["team", "league"], axis=1),
                        matches[["away", "league"]].set_axis(["team", "league"], axis=1)])
    league = league.drop_duplicates("team").set_index("team").league
    teams = pd.DataFrame({"name": profiles.team_names})
    teams["id"] = teams.name.map(slugify)
    teams["league"] = teams.name.map(league)
    if teams.id.duplicated().any():
        raise RuntimeError("two teams share an id")

    usage = (decisions.groupby(["team", "player_id"])
             .agg(decisions=("match_id", "size"), matches=("match_id", "nunique")).reset_index())
    starts = (lineups[lineups.match_id.isin(train_ids)].groupby(["team", "player_id"]).match_id.nunique()
              .rename("starts").reset_index())
    usage = usage.merge(starts, on=["team", "player_id"], how="left").fillna({"starts": 0})
    usage["starts"] = usage.starts.astype(int)
    return dict(matches=matches, lineups=lineups, train_ids=train_ids, teams=teams, usage=usage,
                by_id=dict(zip(teams.id, teams.name)))


# ------------------------------------------------------------------ helpers

def _team_name(team):
    """A team given by id ("atletico-madrid") or by name ("Atletico Madrid", any case or accents)."""
    c = catalog()
    if team in c["by_id"]:
        return c["by_id"][team]
    try:
        return fixture_tools.find_team(simulator().profiles, str(team))
    except KeyError as e:
        raise NotFound(str(e).strip("'\"")) from None


def _team_ref(name):
    t = catalog()["teams"].set_index("name").loc[name]
    return dict(id=t.id, name=name, league=t.league, league_name=LEAGUE_NAMES[t.league])


def _player_ref(player_id, position=None):
    P = simulator().profiles
    row = P.player_lookup.get(int(player_id))
    pos = position or (POSITIONS[P.player_position[row]] if row is not None else None)
    return dict(player_id=int(player_id), name=P.player_names[row] if row is not None else None, position=pos)


def _round(x, digits=4):
    return float(round(float(x), digits))


# ------------------------------------------------------------------ feature 1: profiles

def health():
    sim = simulator()
    c = catalog()
    return dict(status="ok", model=BUNDLE, teams=len(c["teams"]), players=sim.profiles.n_players,
                leagues=[dict(id=k, name=v) for k, v in LEAGUE_NAMES.items()], credit=DATA_CREDIT)


def team_list(league=None):
    teams = catalog()["teams"]
    if league:
        if league not in LEAGUE_NAMES:
            raise BadRequest(f"unknown league '{league}'. Use one of: {', '.join(LEAGUE_NAMES)}")
        teams = teams[teams.league == league]
    return [_team_ref(name) for name in teams.sort_values(["league", "name"]).name]


def _profile_numbers(name):
    P = simulator().profiles
    row = P.team_lookup[name]
    values = {c: P.team_att[:, j] for j, c in enumerate(TEAM_ATT)}
    values.update({c: P.team_def[:, j] for j, c in enumerate(TEAM_DEF)})
    values["press_factor"] = P.press_factor
    numbers = []
    for key, (label, better) in TEAM_NUMBERS.items():
        column = values[key]
        teams_only = column[:-1]                                  # the last row is the average team
        order = np.argsort(-teams_only if better == "higher" else teams_only, kind="stable")
        rank = int(np.flatnonzero(order == row)[0]) + 1
        numbers.append(dict(key=key, label=label, value=_round(column[row]),
                            league_average=_round(column[-1]), better=better,
                            rank=rank, out_of=len(teams_only)))
    return numbers


def _squad(name):
    usage = catalog()["usage"]
    rows = usage[usage.team == name].sort_values(["starts", "decisions"], ascending=False)
    return [dict(**_player_ref(r.player_id), starts=int(r.starts), matches=int(r.matches),
                 decisions=int(r.decisions)) for r in rows.itertuples()]


def usual_xi(name):
    c = catalog()
    return [_player_ref(pid, pos) for pid, pos in fixture_tools.usual_xi(c["lineups"], name, c["train_ids"])]


def team_detail(team):
    name = _team_name(team)
    return dict(**_team_ref(name), profile=_profile_numbers(name), usual_xi=usual_xi(name),
                squad=_squad(name), credit=DATA_CREDIT)


def player_detail(player_id):
    P = simulator().profiles
    try:
        row = P.player_lookup[int(player_id)]
    except (KeyError, ValueError):
        raise NotFound(f"no player with id {player_id}") from None
    position = int(P.player_position[row])
    average = int(P.average_player(position))
    usage = catalog()["usage"]
    teams = usage[usage.player_id == int(player_id)].sort_values("decisions", ascending=False)
    return dict(
        **_player_ref(player_id),
        teams=[dict(**_team_ref(t.team), starts=int(t.starts), matches=int(t.matches), decisions=int(t.decisions))
               for t in teams.itertuples()],
        actions=[dict(action=a, share=_round(P.player_shares[row, j]),
                      position_average=_round(P.player_shares[average, j])) for j, a in enumerate(ACTIONS)],
        involvement=dict(decisions_per_match=_round(P.player_weight[row], 2),
                         position_average=_round(P.player_weight[average], 2)),
        touch_map=dict(
            columns=STYLE_X, rows=STYLE_Y, zone_size_yards=[120 // STYLE_X, 80 // STYLE_Y],
            note="Zone index = column + columns * row. Column 0 is next to the player's own goal, "
                 "the last column next to the opponent's goal; row 0 is y 0 to 20.",
            values=[_round(v) for v in P.player_touch[row]],
            position_average=[_round(v) for v in P.player_touch[average]]),
        credit=DATA_CREDIT)


# ------------------------------------------------------------------ feature 2: simulation

def _parse_xi(xi, side):
    """A starting eleven from the request: 11 items of {player_id, position}."""
    P = simulator().profiles
    if not isinstance(xi, list):
        raise BadRequest(f"{side}_xi must be a list of 11 players")
    pairs = []
    for item in xi:
        try:
            pid, pos = int(item["player_id"]), str(item["position"]).upper()
        except (TypeError, KeyError, ValueError):
            raise BadRequest(f"each {side}_xi item needs player_id and position") from None
        if pid not in P.player_lookup:
            raise BadRequest(f"{side}_xi: no player with id {pid}")
        if pos not in POSITION_ID:
            raise BadRequest(f"{side}_xi: position must be one of {', '.join(POSITIONS)}")
        pairs.append((pid, pos))
    if len({p for p, _ in pairs}) != len(pairs):
        raise BadRequest(f"{side}_xi lists a player twice")
    return pairs


def _event_row(e, fx, labels):
    P = simulator().profiles
    row = int(fx.players[0, e["team"], e["slot"]])
    t = int(e["t"])
    return dict(minute=t // 60 + 1, second=t % 60, team=labels[e["team"]],
                player_id=int(P.player_ids[row]) if row < P.n_players else None,
                player=player_name(P, row), position=POSITIONS[e["position"]],
                action=ACTIONS[e["action"]], result=RESULTS[e["result"]],
                x=_round(e["x"], 1), y=_round(e["y"], 1), end_x=_round(e["end_x"], 1), end_y=_round(e["end_y"], 1),
                under_pressure=bool(e["pressure"]))


def simulate(home, away, rollouts=DEFAULT_ROLLOUTS, seed=None, home_xi=None, away_xi=None, include_events=False):
    """Simulate a fixture `rollouts` times. The first rollout is also returned as a sample match."""
    try:
        rollouts = int(rollouts)
    except (TypeError, ValueError):
        raise BadRequest("rollouts must be a whole number") from None
    if not 1 <= rollouts <= MAX_ROLLOUTS:
        raise BadRequest(f"rollouts must be between 1 and {MAX_ROLLOUTS}")
    home_name, away_name = _team_name(home), _team_name(away)
    if home_name == away_name:
        raise BadRequest("home and away must be different teams")
    if seed is None:
        seed = int(np.random.default_rng().integers(0, 2 ** 31 - 1))
    else:
        try:
            seed = int(seed)
        except (TypeError, ValueError):
            raise BadRequest("seed must be a whole number") from None

    sim, c = simulator(), catalog()
    P = sim.profiles
    xis = []
    for name, given, side in ((home_name, home_xi, "home"), (away_name, away_xi, "away")):
        xis.append(_parse_xi(given, side) if given is not None
                   else fixture_tools.usual_xi(c["lineups"], name, c["train_ids"]))
    try:
        fx = fixture_tools.from_lineups(P, c["lineups"], home_name, away_name, *xis)
    except ValueError as e:
        raise BadRequest(str(e)) from None

    start = time.perf_counter()
    r = sim.run(seed=seed, fixtures=fx.repeat(rollouts), record_first=True)
    seconds = time.perf_counter() - start
    g = r.goals

    scores = pd.Series(list(map(tuple, g))).value_counts().head(TOP_SCORELINES)
    passes = r.passes.sum(axis=0)
    possession = r.ball_seconds / r.ball_seconds.sum(axis=1, keepdims=True)
    labels = ("home", "away")
    average = {labels[s]: dict(goals=_round(g[:, s].mean(), 3), xg=_round(r.xg[:, s].mean(), 3),
                               shots=_round(r.shots[:, s].mean(), 2), passes=_round(r.passes[:, s].mean(), 1),
                               pass_completion=_round(r.completed[:, s].sum() / max(passes[s], 1), 3),
                               possession=_round(possession[:, s].mean(), 3))
               for s in (0, 1)}

    lineups = {labels[s]: [dict(**_player_ref(pid, pos), slot=k) for k, (pid, pos) in enumerate(xis[s])]
               for s in (0, 1)}
    scorers = [dict(team=labels[s], **lineups[labels[s]][k],
                    goals_per_match=_round(r.player_goals[:, s, k].mean(), 3),
                    shots_per_match=_round(r.player_shots[:, s, k].mean(), 2))
               for s in (0, 1) for k in range(fixture_tools.XI)]
    scorers = sorted(scorers, key=lambda p: -p["goals_per_match"])[:TOP_SCORERS]

    events = [_event_row(e, fx, labels) for e in r.events]
    sample = dict(
        score=dict(home=int(g[0, 0]), away=int(g[0, 1])),
        goals=[dict(minute=e["minute"], team=e["team"], player_id=e["player_id"], player=e["player"])
               for e in events if e["result"] == "shot_goal"],
        stats={labels[s]: dict(shots=int(r.shots[0, s]), xg=_round(r.xg[0, s], 2), passes=int(r.passes[0, s]),
                               completed=int(r.completed[0, s]), possession=_round(possession[0, s], 3))
               for s in (0, 1)})
    if include_events:
        sample["events"] = events

    return dict(
        home=_team_ref(home_name), away=_team_ref(away_name), rollouts=rollouts, seed=seed,
        probabilities=dict(home_win=_round((g[:, 0] > g[:, 1]).mean(), 3),
                           draw=_round((g[:, 0] == g[:, 1]).mean(), 3),
                           away_win=_round((g[:, 0] < g[:, 1]).mean(), 3)),
        average=average,
        scorelines=[dict(home=int(h), away=int(a), probability=_round(n / rollouts, 3)) for (h, a), n in scores.items()],
        likely_scorers=scorers, lineups=lineups, sample_match=sample,
        seconds=_round(seconds, 2), model=BUNDLE, credit=DATA_CREDIT)


def simulate_request(data):
    """Validate a POST body and run the simulation."""
    if not isinstance(data, dict):
        raise BadRequest("send a JSON object")
    missing = [k for k in ("home", "away") if not data.get(k)]
    if missing:
        raise BadRequest(f"missing field(s): {', '.join(missing)}")
    unknown = set(data) - {"home", "away", "rollouts", "seed", "home_xi", "away_xi", "include_events"}
    if unknown:
        raise BadRequest(f"unknown field(s): {', '.join(sorted(unknown))}")
    include = data.get("include_events", False)
    if not isinstance(include, bool):
        raise BadRequest("include_events must be true or false")
    return simulate(data["home"], data["away"], data.get("rollouts", DEFAULT_ROLLOUTS), data.get("seed"),
                    data.get("home_xi"), data.get("away_xi"), include)
