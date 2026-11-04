"""Tests for the simulator. They need trained models, so they skip on a fresh checkout."""
import numpy as np
import pytest

from metafut.config import MODEL_DIR

pytestmark = pytest.mark.skipif(not (MODEL_DIR / "simulator_v0.joblib").exists(),
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
