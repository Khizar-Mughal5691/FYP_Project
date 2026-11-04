"""Tests for turning raw events into decisions, using small hand-written events."""
import numpy as np

from metafut.data.actions import match_decisions, position_group


def event(index, kind, team, minute=1, second=0, location=(60.0, 40.0), period=1, **extra):
    e = dict(index=index, period=period, minute=minute, second=second, type=dict(name=kind),
             team=dict(name=team), player=dict(id=index, name=f"P{index}"),
             position=dict(name="Center Forward"), location=list(location) if location else None)
    e.update(extra)
    return e


def passed(end, outcome=None, kind=None):
    p = dict(end_location=list(end), angle=0.0, length=10.0, height=dict(name="Ground Pass"))
    if outcome:
        p["outcome"] = dict(name=outcome)
    if kind:
        p["type"] = dict(name=kind)
    return p


GOAL = dict(outcome=dict(name="Goal"), statsbomb_xg=0.5)


def test_position_groups():
    assert position_group("Goalkeeper") == "GK"
    assert position_group("Left Back") == "DEF"
    assert position_group("Right Wing Back") == "DEF"
    assert position_group("Center Defensive Midfield") == "MID"
    assert position_group("Left Wing") == "FWD"
    assert position_group(None) == "MID"


def test_results_and_phases():
    events = [event(1, "Pass", "A", **{"pass": passed((70, 40), kind="Kick Off")}),
              event(2, "Pass", "A", second=5, **{"pass": passed((80, 40), "Incomplete")}),
              event(3, "Pass", "B", second=9, **{"pass": passed((80, 40), "Out")}),
              event(4, "Pass", "B", second=20, **{"pass": passed((80, 40), "Injury Clearance")})]
    d = match_decisions(events, 1, "A")
    assert list(d.result) == ["pass_complete", "pass_incomplete", "pass_out", "pass_out"]
    assert list(d.phase) == ["kick_off", "open", "open", "open"]
    assert list(d.label_valid) == [True, True, True, False]
    assert list(d.is_home) == [1, 1, 0, 0]


def test_previous_and_next_are_linked():
    events = [event(1, "Pass", "A", **{"pass": passed((70, 40))}),
              event(2, "Carry", "A", second=3, location=(70, 40), carry=dict(end_location=[75, 40])),
              event(3, "Dispossessed", "A", second=6, location=(75, 40)),
              event(4, "Pass", "B", second=8, location=(45, 40), **{"pass": passed((50, 40))})]
    d = match_decisions(events, 1, "A")
    assert list(d.prev_result) == ["start", "pass_complete", "carry", "loss"]
    assert list(d.prev_same_team) == [0, 1, 1, 0]
    assert list(d.next_same_team)[:3] == [1, 1, 0]
    assert d.dt.iloc[0] == 3
    assert d.has_next.iloc[-1] == 0
    assert d.prev_height.iloc[1] == "ground"
    assert d.prev_height.iloc[2] == "none"


def test_score_is_tracked_before_each_decision():
    events = [event(1, "Shot", "A", shot=GOAL),
              event(2, "Pass", "B", second=30, **{"pass": passed((60, 50))}),
              event(3, "Pass", "A", second=40, **{"pass": passed((60, 50))})]
    d = match_decisions(events, 1, "A")
    assert list(d.score_diff) == [0, -1, 1]
    assert d.result.iloc[0] == "shot_goal"


def test_second_half_starts_fresh_and_penalties_are_marked():
    events = [event(1, "Pass", "A", **{"pass": passed((70, 40))}),
              event(2, "Shot", "A", minute=46, period=2, location=(108, 40),
                    shot=dict(outcome=dict(name="Saved"), type=dict(name="Penalty")))]
    d = match_decisions(events, 1, "A")
    assert d.prev_result.iloc[1] == "start"
    assert d.has_next.iloc[0] == 0
    assert d.phase.iloc[1] == "penalty"
    assert np.isnan(d.end_x.iloc[1])


def test_events_without_location_and_shootouts_are_ignored():
    events = [event(1, "Pass", "A", **{"pass": passed((70, 40))}),
              event(2, "Shot", "A", period=5, shot=GOAL),
              event(3, "Clearance", "B", location=None)]
    d = match_decisions(events, 1, "A")
    assert len(d) == 1
