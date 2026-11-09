"""Turn raw StatsBomb events into one table of on-ball decisions.

Each row is a decision by the player on the ball (pass, carry, dribble, shot, loss of control,
clearance) plus the game state before it and what the next decision was. Locations are in the
attacking direction of the acting team, as StatsBomb records them.
"""
import gzip
import json
from difflib import SequenceMatcher

import numpy as np
import pandas as pd

from metafut.config import LEAGUES, RAW_DIR, TABLE_DIR, TRAIN_FRACTION, VAL_FRACTION

DECISION_TYPES = {"Pass": "pass", "Carry": "carry", "Dribble": "dribble", "Shot": "shot",
                  "Miscontrol": "loss", "Dispossessed": "loss", "Clearance": "clear"}
PASS_PHASES = {"Kick Off": "kick_off", "Throw-in": "throw_in", "Goal Kick": "goal_kick",
               "Corner": "corner", "Free Kick": "free_kick"}
SHOT_PHASES = {"Penalty": "penalty", "Free Kick": "free_kick", "Corner": "corner",
               "Kick Off": "kick_off"}
HEIGHT_NAMES = {"Ground Pass": "ground", "Low Pass": "low", "High Pass": "high"}


def position_group(name):
    if not name:
        return "MID"
    if name == "Goalkeeper":
        return "GK"
    if "Back" in name:
        return "DEF"
    if "Wing" in name or "Forward" in name or "Striker" in name:
        return "FWD"
    return "MID"


def _pass_result(outcome):
    # Unknown and Injury Clearance are not real failures; they stay in the chain but not in training.
    if outcome is None:
        return "pass_complete"
    if outcome in ("Out", "Injury Clearance"):
        return "pass_out"
    if outcome == "Pass Offside":
        return "pass_offside"
    return "pass_incomplete"


def _parse(ev, action):
    """Extract result, phase and end location of a decision event."""
    row = dict(result=action, phase="open", end_x=np.nan, end_y=np.nan, angle=np.nan,
               length=np.nan, height="none", label_valid=True, xg=np.nan)
    if action == "pass":
        p = ev["pass"]
        outcome = p.get("outcome", {}).get("name")
        row["result"] = _pass_result(outcome)
        row["label_valid"] = outcome not in ("Unknown", "Injury Clearance")
        row["phase"] = PASS_PHASES.get(p.get("type", {}).get("name"), "open")
        row["end_x"], row["end_y"] = p["end_location"][:2]
        row["angle"], row["length"] = p["angle"], p["length"]
        row["height"] = HEIGHT_NAMES.get(p.get("height", {}).get("name"), "ground")
    elif action == "carry":
        row["end_x"], row["end_y"] = ev["carry"]["end_location"][:2]
    elif action == "dribble":
        ok = ev["dribble"].get("outcome", {}).get("name") == "Complete"
        row["result"] = "dribble_success" if ok else "dribble_fail"
    elif action == "shot":
        s = ev["shot"]
        row["result"] = "shot_goal" if s["outcome"]["name"] == "Goal" else "shot_nogoal"
        row["phase"] = SHOT_PHASES.get(s.get("type", {}).get("name"), "open")
        row["xg"] = s.get("statsbomb_xg", np.nan)
    return row


def canonical_teams(events, home_team, away_team):
    """Map every team name used in a match's events to its home or away name.

    A few matches spell a team differently in their events ("Marseille") than in the match list
    ("Olympique de Marseille"). Without this, the home team would look like a third team.
    """
    seen = list(dict.fromkeys(ev["team"]["name"] for ev in events if ev.get("team")))
    mapping = {home_team: home_team, away_team: away_team}
    unknown = [name for name in seen if name not in mapping]
    free = [name for name in (home_team, away_team) if name not in seen]
    if len(unknown) > len(free):
        raise ValueError(f"cannot match teams {unknown} to {free}")
    for name in unknown:
        best = max(free, key=lambda f: SequenceMatcher(None, name.lower(), f.lower()).ratio())
        mapping[name] = best
        free.remove(best)
    return mapping


def match_decisions(events, match_id, home_team, away_team):
    """All decisions of one match, in order, with the state before each one."""
    events = sorted(events, key=lambda e: e["index"])
    names = canonical_teams(events, home_team, away_team)
    other_team = {home_team: away_team, away_team: home_team}
    rows, goals = [], {}
    for ev in events:
        name = ev["type"]["name"]
        team = names.get(ev.get("team", {}).get("name"))
        if ev["period"] <= 2 and name in DECISION_TYPES and ev.get("location"):
            action = DECISION_TYPES[name]
            own, opp = goals.get(team, 0), goals.get(other_team[team], 0)
            rows.append(dict(
                match_id=match_id, period=ev["period"],
                t=ev["minute"] * 60 + ev["second"], team=team, opp=other_team[team],
                is_home=int(team == home_team),
                player_id=ev.get("player", {}).get("id", -1),
                player=ev.get("player", {}).get("name", ""),
                position=position_group(ev.get("position", {}).get("name")),
                x=float(ev["location"][0]), y=float(ev["location"][1]),
                action=action, pressure=int(bool(ev.get("under_pressure"))),
                score_diff=own - opp, **_parse(ev, action)))
        if name == "Shot" and ev["shot"]["outcome"]["name"] == "Goal":
            goals[team] = goals.get(team, 0) + 1
        elif name == "Own Goal For":
            goals[team] = goals.get(team, 0) + 1
    if not rows:
        return pd.DataFrame()
    return _link(pd.DataFrame(rows))


def _link(d):
    """Add the previous decision and the next decision to every row."""
    same_period_prev = d.period == d.period.shift()
    d["prev_result"] = d.result.shift().where(same_period_prev, "start")
    d["prev_same_team"] = ((d.team == d.team.shift()) & same_period_prev).astype(int)
    prev_height = d.height.shift().where(d.result.shift() == "pass_complete", "none")
    d["prev_height"] = prev_height.where(same_period_prev, "none")

    same_period_next = d.period == d.period.shift(-1)
    d["next_same_team"] = (d.team == d.team.shift(-1)).astype(int)
    d["next_x"], d["next_y"] = d.x.shift(-1), d.y.shift(-1)
    d["next_phase"] = d.phase.shift(-1)
    d["next_position"] = d.position.shift(-1)
    # After a carry the same player usually acts again; after a pass a teammate does.
    d["next_same_player"] = ((d.player_id == d.player_id.shift(-1))
                             & (d.team == d.team.shift(-1))).astype(int)
    d["dt"] = (d.t.shift(-1) - d.t).clip(lower=0)
    d["has_next"] = same_period_next.astype(int)
    return d


def _split_labels(matches):
    """Date-ordered train / val / test labels for one league's matches."""
    ordered = sorted(matches, key=lambda m: (m["match_date"], m["match_id"]))
    n = len(ordered)
    a, b = int(n * TRAIN_FRACTION), int(n * (TRAIN_FRACTION + VAL_FRACTION))
    return {m["match_id"]: ("train" if i < a else "val" if i < b else "test")
            for i, m in enumerate(ordered)}


def build_tables(progress=print):
    """Write decisions.parquet, matches.parquet and lineups.parquet."""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    frames, match_rows, lineup_rows = [], [], []
    for league in LEAGUES:
        matches = json.loads((RAW_DIR / "matches" / f"{league}.json").read_text(encoding="utf-8"))
        labels = _split_labels(matches)
        for m in matches:
            mid = m["match_id"]
            with gzip.open(RAW_DIR / "events" / f"{mid}.json.gz", "rt", encoding="utf-8") as f:
                events = json.load(f)
            home = m["home_team"]["home_team_name"]
            away = m["away_team"]["away_team_name"]
            d = match_decisions(events, mid, home, away)
            d["league"], d["split"] = league, labels[mid]
            frames.append(d)
            match_rows.append(dict(match_id=mid, league=league, split=labels[mid],
                                   date=m["match_date"], home=home, away=away,
                                   home_goals=m["home_score"], away_goals=m["away_score"]))
            names = canonical_teams(events, home, away)
            for ev in events:
                if ev["type"]["name"] != "Starting XI":
                    continue
                for p in ev["tactics"]["lineup"]:
                    lineup_rows.append(dict(
                        match_id=mid, team=names[ev["team"]["name"]],
                        formation=ev["tactics"]["formation"], player_id=p["player"]["id"],
                        player=p["player"]["name"], position_name=p["position"]["name"],
                        position=position_group(p["position"]["name"])))
        progress(f"{league}: {len(matches)} matches")
    table = pd.concat(frames, ignore_index=True)
    table.to_parquet(TABLE_DIR / "decisions.parquet", index=False)
    pd.DataFrame(match_rows).to_parquet(TABLE_DIR / "matches.parquet", index=False)
    pd.DataFrame(lineup_rows).to_parquet(TABLE_DIR / "lineups.parquet", index=False)
    return table
