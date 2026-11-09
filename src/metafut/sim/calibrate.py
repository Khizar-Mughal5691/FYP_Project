"""Calibrate the composed simulator on training matches.

Each model and pool matches its own training data, but chaining two thousand decisions per match
lets small biases add up: the simulator takes more shots than real teams do. One number, the
shot scale, multiplies the action model's shot probability. It is fitted so that simulated
training fixtures (real teams, real starting elevens) produce as many shots per match as those
matches really had. Validation and test matches are never used here.
"""
import numpy as np
import pandas as pd

from metafut.config import TABLE_DIR
from metafut.sim import fixtures as fixture_tools


def calibrate_shots(sim, n_fixtures=300, rollouts=4, iterations=3, seed=0, progress=print):
    """Fit tables["shot_scale"] on training fixtures. Returns a log of each iteration."""
    matches = pd.read_parquet(TABLE_DIR / "matches.parquet")
    lineups = pd.read_parquet(TABLE_DIR / "lineups.parquet")
    decisions = pd.read_parquet(TABLE_DIR / "decisions.parquet", columns=["match_id", "action", "split"])
    train = matches[matches.split == "train"].sample(n_fixtures, random_state=seed)
    real = decisions[decisions.match_id.isin(train.match_id) & (decisions.action == "shot")]
    real_shots = len(real) / n_fixtures
    fx = fixture_tools.real_matches(sim.profiles, train.match_id.tolist(), lineups, matches).repeat(rollouts)

    log = []
    sim.tables["shot_scale"] = 1.0
    for step in range(iterations):
        simulated = sim.run(seed=seed + step, fixtures=fx).shots.sum(axis=1).mean()
        log.append(dict(step=step, shot_scale=round(sim.tables["shot_scale"], 4),
                        simulated_shots=round(float(simulated), 2), real_shots=round(real_shots, 2)))
        progress(f"calibration step {step}: scale {sim.tables['shot_scale']:.4f}, "
                 f"simulated {simulated:.2f} shots, real {real_shots:.2f}")
        sim.tables["shot_scale"] *= real_shots / simulated
    return log
