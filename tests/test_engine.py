"""Tests for the simulator. They need trained models, so they skip on a fresh checkout."""
import numpy as np
import pytest

from metafut.config import BUNDLE, MODEL_DIR

pytestmark = pytest.mark.skipif(not (MODEL_DIR / BUNDLE).exists(),
                                reason="run scripts/03_train_models.py first")


@pytest.fixture(scope="module")
def sim():
    from metafut.sim.engine import Simulator
    return Simulator()


def test_same_seed_gives_the_same_matches(sim):
    a, b = sim.run(5, seed=11), sim.run(5, seed=11)
    assert (a.goals == b.goals).all()
    assert (a.passes == b.passes).all()


def test_different_seeds_give_different_matches(sim):
    assert (sim.run(5, seed=1).passes != sim.run(5, seed=2).passes).any()


def test_a_match_plays_both_halves(sim):
    r = sim.run(1, seed=3, record_first=True)
    times = [e["t"] for e in r.events]
    assert min(times) < 60
    assert max(times) > 85 * 60
    assert sum(1 for a, b in zip(times, times[1:]) if b < a) == 0


def test_counts_are_consistent(sim):
    r = sim.run(20, seed=4)
    assert (r.completed <= r.passes).all()
    assert (r.goals <= r.shots).all()
    assert (r.passes + r.carries + r.shots + r.dribbles <= r.decisions).all()
    assert np.isfinite(r.xg).all() and (r.xg >= 0).all()


def test_every_event_stays_on_the_pitch(sim):
    r = sim.run(1, seed=5, record_first=True)
    assert all(0 <= e["x"] <= 120 and 0 <= e["y"] <= 80 for e in r.events)


def test_player_totals_add_up_to_team_totals(sim):
    from metafut.sim import fixtures as F
    r = sim.run(seed=6, fixtures=F.fixture(sim.profiles, "Barcelona", "Real Madrid").repeat(10))
    assert (r.player_goals.sum(axis=2) == r.goals).all()
    assert (r.player_shots.sum(axis=2) == r.shots).all()
    assert (r.player_passes.sum(axis=2) == r.passes).all()
    assert (r.player_decisions.sum(axis=2) == r.decisions).all()


def test_a_stronger_team_wins_more_often(sim):
    from metafut.sim import fixtures as F
    # Barcelona won La Liga 2015/16; Levante finished last.
    r = sim.run(seed=8, fixtures=F.fixture(sim.profiles, "Barcelona", "Levante UD").repeat(200))
    home, away = (r.goals[:, 0] > r.goals[:, 1]).mean(), (r.goals[:, 0] < r.goals[:, 1]).mean()
    assert home > 2 * away
    assert r.passes[:, 0].mean() > r.passes[:, 1].mean()


def test_trace_records_every_decision(sim):
    r = sim.run(3, seed=9, trace=True)
    assert len(r.trace["match"]) == r.decisions.sum()
    assert set(np.unique(r.trace["match"])) == {0, 1, 2}
