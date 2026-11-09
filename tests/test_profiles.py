"""Tests for team and player profiles, fixtures and choosing who gets the ball, on small made-up data."""
import numpy as np
import pandas as pd
import pytest

from metafut.config import ACTIONS, PHASE_ID, POSITION_ID, RESULT_ID
from metafut.models.features import PLAYER_COLS, TEAM_ATT
from metafut.models.profiles import attach, build_profiles
from metafut.sim import fixtures as F
from metafut.sim.engine import choose_players

POS = ["GK", "DEF", "DEF", "DEF", "DEF", "MID", "MID", "MID", "FWD", "FWD", "FWD"]


def decisions(seed=0):
    """Two teams, two matches; team A completes every pass in match 1 and none in match 2."""
    rng = np.random.default_rng(seed)
    rows = []
    for match in (1, 2):
        for team, opp, base in (("A", "B", 100), ("B", "A", 200)):
            for k in range(220):
                slot = k % 11
                action = ACTIONS[k % len(ACTIONS)] if slot else "pass"
                done = (match == 1) if team == "A" else bool(k % 2)
                rows.append(dict(
                    match_id=match, team=team, opp=opp, player_id=base + slot, player=f"{team}{slot}",
                    position=POS[slot], action=action, label_valid=True, pressure=int(k % 3 == 0),
                    phase="open", x=float(rng.uniform(5, 115)), y=float(rng.uniform(5, 75)),
                    angle=float(rng.uniform(-3, 3)), height="ground",
                    result="pass_complete" if action == "pass" and done else
                           ("pass_incomplete" if action == "pass" else action if action != "dribble" else "dribble_success")))
    d = pd.DataFrame(rows)
    d["end_x"], d["end_y"] = d.x + 3, d.y
    d["position_id"] = d.position.map(POSITION_ID)
    d["phase_id"] = PHASE_ID["open"]
    d["height_id"] = 1
    d["prev_id"] = RESULT_ID["start"]
    return d


def test_training_rows_never_see_their_own_match():
    profiles, tr = build_profiles(decisions())
    a = tr[tr.team == "A"]
    # Rows from match 1 (all passes completed) only see match 2 (none completed), and vice versa.
    assert a[a.match_id == 1].att_pass.mean() < a[a.match_id == 2].att_pass.mean()


def test_rows_outside_training_get_the_full_profile():
    profiles, tr = build_profiles(decisions())
    out = attach(profiles, decisions(seed=1))
    a = out[out.team == "A"]
    assert np.allclose(a[TEAM_ATT].to_numpy(), a[TEAM_ATT].to_numpy()[0])


def test_player_profiles_are_distributions():
    profiles, _ = build_profiles(decisions())
    assert np.allclose(profiles.player_shares.sum(axis=1), 1)
    assert np.allclose(profiles.player_touch.sum(axis=1), 1)
    assert (profiles.player_weight > 0).all()


def test_unseen_player_and_team_get_averages():
    profiles, _ = build_profiles(decisions())
    rows = profiles.player_index([999, 100], [POSITION_ID["FWD"], POSITION_ID["GK"]])
    assert rows[0] == profiles.average_player(POSITION_ID["FWD"])
    assert rows[1] == profiles.player_lookup[100]
    assert profiles.team_index(["Nobody"])[0] == profiles.average_team
    out = attach(profiles, decisions().assign(player_id=999))
    fwd = out[out.position == "FWD"]
    assert np.allclose(fwd[PLAYER_COLS].to_numpy(), profiles.player_shares[profiles.average_player(POSITION_ID["FWD"])])


def lineups():
    rows = []
    for match in (1, 2, 3):
        for team, base in (("A", 100), ("B", 200)):
            for slot, pos in enumerate(POS):
                # In match 3 team A plays a reserve keeper and a reserve striker.
                pid = base + slot
                if match == 3 and team == "A" and slot in (0, 10):
                    pid = 900 + slot
                rows.append(dict(match_id=match, team=team, player_id=pid, position=pos, formation=433))
    return pd.DataFrame(rows)


def test_usual_xi_takes_the_most_frequent_starters():
    xi = F.usual_xi(lineups(), "A", [1, 2, 3])
    ids = [p for p, _ in xi]
    assert len(xi) == 11
    assert sum(1 for _, pos in xi if pos == "GK") == 1
    assert 100 in ids and 900 not in ids and 910 not in ids


def test_fixture_checks_its_elevens():
    profiles, _ = build_profiles(decisions())
    xi = list(zip(range(100, 111), POS))
    f = F.from_lineups(profiles, lineups(), "A", "B", xi, list(zip(range(200, 211), POS)))
    assert f.players.shape == (1, 2, 11)
    with pytest.raises(ValueError):
        F.from_lineups(profiles, lineups(), "A", "B", xi[:10], xi)
    with pytest.raises(ValueError):
        F.from_lineups(profiles, lineups(), "A", "B", [(1, "GK")] * 11, xi)
    assert f.repeat(3).players.shape == (3, 2, 11)


def test_average_fixture_has_one_keeper_a_side():
    profiles, _ = build_profiles(decisions())
    f = F.average(4, profiles)
    assert f.teams.shape == (4, 2)
    assert ((f.positions == POSITION_ID["GK"]).sum(axis=2) == 1).all()


def test_find_team_ignores_case_and_accents():
    profiles, _ = build_profiles(decisions())
    profiles.team_names = ["Atlético Madrid", "Real Madrid"]
    assert F.find_team(profiles, "atletico madrid") == "Atlético Madrid"
    with pytest.raises(KeyError):
        F.find_team(profiles, "Madrid")


def test_choose_players_respects_group_weights_and_exclusion():
    rng = np.random.default_rng(0)
    positions = np.tile(np.array([POSITION_ID[p] for p in POS]), (2000, 1))
    weights = np.ones((2000, 11))
    weights[:, 9] = 9.0                       # one forward sees much more of the ball
    group = np.full(2000, POSITION_ID["FWD"])
    picked = choose_players(rng, positions, weights, group)
    assert set(picked) <= {8, 9, 10}
    assert (picked == 9).mean() > 0.7
    picked = choose_players(rng, positions, weights, group, exclude=np.full(2000, 9))
    assert 9 not in set(picked)
    # Nobody in the group: any outfield player, never the keeper.
    no_fwd = positions.copy()
    no_fwd[no_fwd == POSITION_ID["FWD"]] = POSITION_ID["MID"]
    picked = choose_players(rng, no_fwd, weights, group)
    assert 0 not in set(picked)
