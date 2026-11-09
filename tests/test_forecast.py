"""Tests for forecast scoring, the Dixon-Coles baseline and matching bookmaker odds."""
import numpy as np
import pandas as pd

from metafut.eval.forecast import (DixonColes, fixed_rates, from_simulation, log_score, match_odds,
                                   outcome, paired_interval, rps)


def test_rps_is_zero_for_a_certain_correct_forecast_and_worst_for_the_opposite():
    assert rps([[1, 0, 0]], [0])[0] == 0
    assert rps([[0, 0, 1]], [0])[0] == 1
    # A draw forecast for a home win is half as wrong as an away forecast.
    assert np.isclose(rps([[0, 1, 0]], [0])[0], 0.5)


def test_rps_of_a_known_example():
    # Cumulative forecast (0.5, 0.8) against a draw (0, 1): ((0.5)^2 + (0.2)^2) / 2 = 0.145
    assert np.isclose(rps([[0.5, 0.3, 0.2]], [1])[0], 0.145)


def test_outcome_and_log_score():
    assert list(outcome([2, 1, 0], [1, 1, 3])) == [0, 1, 2]
    assert np.isclose(log_score([[0.5, 0.25, 0.25]], [0])[0], np.log(2))


def test_fixed_rates_sum_to_one():
    m = pd.DataFrame(dict(home_goals=[1, 0, 2, 1], away_goals=[0, 0, 3, 1]))
    assert np.allclose(fixed_rates(m), [0.25, 0.5, 0.25])


def test_simulated_probabilities_never_reach_zero():
    goals = np.zeros((2, 10, 2), dtype=int)
    goals[0, :, 0] = 1          # the first fixture is always a home win
    p = from_simulation(goals)
    assert np.allclose(p.sum(axis=1), 1)
    assert (p > 0).all()
    assert p[0, 0] > 0.9 and p[1, 1] > 0.9


def test_paired_interval_contains_the_true_difference():
    rng = np.random.default_rng(0)
    a = rng.normal(0.2, 0.05, 500)
    b = a - 0.03 + rng.normal(0, 0.05, 500)
    low, high = paired_interval(a, b)
    assert low < 0.03 < high
    assert high - low < 0.02


def test_dixon_coles_rates_a_stronger_team_higher():
    rng = np.random.default_rng(1)
    rows = []
    for _ in range(60):
        for home, away in [("Strong", "Weak"), ("Weak", "Strong"), ("Strong", "Mid"), ("Mid", "Weak"),
                           ("Mid", "Strong"), ("Weak", "Mid")]:
            attack = {"Strong": 2.2, "Mid": 1.3, "Weak": 0.7}
            rows.append(dict(home=home, away=away, home_goals=rng.poisson(attack[home]),
                             away_goals=rng.poisson(attack[away] * 0.9)))
    model = DixonColes().fit(pd.DataFrame(rows))
    p = model.predict(["Strong", "Weak", "Unknown"], ["Weak", "Strong", "Strong"])
    assert np.allclose(p.sum(axis=1), 1)
    assert p[0, 0] > 0.6           # Strong at home to Weak wins most of the time
    assert p[1, 2] > p[1, 0]       # Weak at home to Strong loses more often than it wins
    assert p[2, 2] > p[2, 0]       # an unknown team counts as average, below Strong


def test_odds_are_matched_by_date_and_score_even_when_names_differ():
    matches = pd.DataFrame(dict(match_id=[1, 2], date=["2016-01-10", "2016-01-10"],
                                home=["Manchester United", "Olympique de Marseille"],
                                away=["Leicester City", "AS Monaco"], home_goals=[1, 0], away_goals=[1, 2]))
    odds = pd.DataFrame(dict(date=pd.to_datetime(["2016-01-10", "2016-01-11", "2016-01-10"]),
                             home=["Man United", "Marseille", "Chelsea"], away=["Leicester", "Monaco", "Everton"],
                             home_goals=[1, 0, 1], away_goals=[1, 2, 1],
                             p_home=[0.5, 0.3, 0.6], p_draw=[0.3, 0.3, 0.2], p_away=[0.2, 0.4, 0.2]))
    out = match_odds(matches, odds).set_index("match_id")
    assert out.loc[1, "odds_home"] == "Man United"     # Chelsea 1-1 Everton has the same date and score
    assert out.loc[2, "odds_home"] == "Marseille"      # a day later in the odds file
    assert len(out) == 2
