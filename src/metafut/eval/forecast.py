"""Match forecasts, the baselines they are compared with, and how they are scored.

A forecast gives three probabilities: home win, draw, away win. The ranked probability score
(RPS) compares them with what happened and treats the outcomes as ordered, so predicting a draw
when the home team won is less wrong than predicting an away win. 0 is perfect; lower is better.

Baselines, from weakest to strongest:
- fixed rates: the same home, draw and away shares for every match, from training matches
- Dixon-Coles: a well-known statistical model with an attack and defence rating per team
- bookmaker odds: the betting market's view, usually the hardest benchmark to beat
"""
import unicodedata
from difflib import SequenceMatcher

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

from metafut.config import RAW_DIR

HOME, DRAW, AWAY = 0, 1, 2
MAX_GOALS = 10


def outcome(home_goals, away_goals):
    h, a = np.asarray(home_goals), np.asarray(away_goals)
    return np.where(h > a, HOME, np.where(h == a, DRAW, AWAY))


def rps(probs, outcomes):
    """Ranked probability score per match, for (home, draw, away) probabilities."""
    probs = np.asarray(probs, dtype=np.float64)
    observed = np.eye(3)[np.asarray(outcomes)]
    gap = np.cumsum(probs, axis=1)[:, :2] - np.cumsum(observed, axis=1)[:, :2]
    return (gap ** 2).sum(axis=1) / 2


def log_score(probs, outcomes):
    """Negative log probability given to what happened, per match. Lower is better."""
    p = np.asarray(probs, dtype=np.float64)[np.arange(len(outcomes)), np.asarray(outcomes)]
    return -np.log(np.clip(p, 1e-9, 1))


def fixed_rates(train_matches):
    counts = np.bincount(outcome(train_matches.home_goals, train_matches.away_goals), minlength=3)
    return counts / counts.sum()


def from_simulation(goals, laplace=1 / 3):
    """Home, draw and away probabilities from simulated scores of shape (matches, rollouts, 2).
    A small count is added to each outcome so no outcome gets probability zero."""
    home = (goals[..., 0] > goals[..., 1]).sum(axis=1)
    draw = (goals[..., 0] == goals[..., 1]).sum(axis=1)
    away = (goals[..., 0] < goals[..., 1]).sum(axis=1)
    counts = np.column_stack([home, draw, away]) + laplace
    return counts / counts.sum(axis=1, keepdims=True)


def paired_interval(a, b, draws=2000, seed=0):
    """95% interval for mean(a - b), resampling matches."""
    rng = np.random.default_rng(seed)
    diff = np.asarray(a) - np.asarray(b)
    means = diff[rng.integers(0, len(diff), (draws, len(diff)))].mean(axis=1)
    return [round(float(np.percentile(means, 2.5)), 4), round(float(np.percentile(means, 97.5)), 4)]


class DixonColes:
    """Dixon and Coles (1997): goals are Poisson with team attack and defence ratings and a home
    advantage, plus a correction for low scores (0-0, 1-0, 0-1, 1-1). Fitted on one league."""

    def __init__(self, ridge=1e-3):
        self.ridge = ridge

    def _rates(self, params, home, away):
        n = len(self.teams)
        base, adv = params[0], params[1]
        attack, defence = params[2:2 + n], params[2 + n:2 + 2 * n]
        lam = np.exp(base + adv + attack[home] - defence[away])
        mu = np.exp(base + attack[away] - defence[home])
        return lam, mu

    @staticmethod
    def _tau(x, y, lam, mu, rho):
        tau = np.ones_like(lam)
        tau = np.where((x == 0) & (y == 0), 1 - lam * mu * rho, tau)
        tau = np.where((x == 0) & (y == 1), 1 + lam * rho, tau)
        tau = np.where((x == 1) & (y == 0), 1 + mu * rho, tau)
        tau = np.where((x == 1) & (y == 1), 1 - rho, tau)
        return np.clip(tau, 1e-6, None)

    def fit(self, matches):
        self.teams = sorted(set(matches.home) | set(matches.away))
        index = {t: i for i, t in enumerate(self.teams)}
        home = matches.home.map(index).to_numpy()
        away = matches.away.map(index).to_numpy()
        x, y = matches.home_goals.to_numpy(), matches.away_goals.to_numpy()
        n = len(self.teams)

        def loss(params):
            lam, mu = self._rates(params, home, away)
            ll = (np.log(self._tau(x, y, lam, mu, params[-1])) + poisson.logpmf(x, lam)
                  + poisson.logpmf(y, mu)).sum()
            return -ll + self.ridge * (params[2:2 + 2 * n] ** 2).sum()

        start = np.zeros(2 + 2 * n + 1)
        start[0] = np.log(max((x.mean() + y.mean()) / 2, 0.1))
        bounds = [(None, None)] * (2 + 2 * n) + [(-0.25, 0.25)]
        self.params = minimize(loss, start, method="L-BFGS-B", bounds=bounds).x
        self.index = index
        return self

    def predict(self, home_teams, away_teams):
        """(home, draw, away) probabilities. Unknown teams get average ratings."""
        n = len(self.teams)
        base, adv = self.params[0], self.params[1]
        attack = np.append(self.params[2:2 + n], 0.0)     # row n: an unknown team, average rating
        defence = np.append(self.params[2 + n:2 + 2 * n], 0.0)
        h = np.array([self.index.get(t, n) for t in home_teams])
        a = np.array([self.index.get(t, n) for t in away_teams])
        lam = np.exp(base + adv + attack[h] - defence[a])[:, None, None]
        mu = np.exp(base + attack[a] - defence[h])[:, None, None]
        goals = np.arange(MAX_GOALS + 1)
        gx, gy = np.meshgrid(goals, goals, indexing="ij")
        grid = poisson.pmf(gx[None], lam) * poisson.pmf(gy[None], mu)
        grid *= self._tau(gx[None], gy[None], lam, mu, self.params[-1])
        grid /= grid.sum(axis=(1, 2), keepdims=True)
        return np.column_stack([(grid * (gx > gy)).sum(axis=(1, 2)), (grid * (gx == gy)).sum(axis=(1, 2)),
                                (grid * (gx < gy)).sum(axis=(1, 2))])


# ---------------------------------------------------------------- bookmaker odds

ODDS_CODES = {"premier_league": "E0", "la_liga": "SP1", "serie_a": "I1", "ligue_1": "F1"}
ODDS_COLUMNS = [("PSH", "PSD", "PSA"), ("B365H", "B365D", "B365A"), ("BbAvH", "BbAvD", "BbAvA")]


def _plain(name):
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return " ".join("".join(c if c.isalnum() else " " for c in text).split())


def _similar(a, b):
    return SequenceMatcher(None, _plain(a), _plain(b)).ratio()


def load_odds(league):
    """Bookmaker probabilities for one league from football-data.co.uk, with the margin removed.
    Returns None when the file has not been downloaded."""
    path = RAW_DIR / "odds" / f"{league}.csv"
    if not path.exists():
        return None
    raw = pd.read_csv(path, encoding="latin-1")
    cols = next(c for c in ODDS_COLUMNS if all(k in raw.columns for k in c))
    inverse = 1 / raw[list(cols)].to_numpy(dtype=np.float64)
    probs = inverse / inverse.sum(axis=1, keepdims=True)
    # Dates are day/month with a two- or four-digit year.
    date = pd.to_datetime(raw.Date, format="%d/%m/%y", errors="coerce").fillna(
        pd.to_datetime(raw.Date, format="%d/%m/%Y", errors="coerce"))
    return pd.DataFrame(dict(date=date, home=raw.HomeTeam,
                             away=raw.AwayTeam, home_goals=raw.FTHG, away_goals=raw.FTAG,
                             p_home=probs[:, 0], p_draw=probs[:, 1], p_away=probs[:, 2],
                             source=cols[0][:-1]))


def _candidates(odds, m, days):
    near = abs((odds.date - pd.Timestamp(m.date)).dt.days) <= days
    return odds[near & (odds.home_goals == m.home_goals) & (odds.away_goals == m.away_goals)]


def team_name_map(matches, odds):
    """StatsBomb team name -> odds file team name. Learned from matches that only one odds row
    fits by date and score; any team still unmapped takes the most similar unused name."""
    votes = {}
    for m in matches.itertuples():
        cand = _candidates(odds, m, 1)
        if len(cand) == 1:
            c = cand.iloc[0]
            for pair in ((m.home, c.home), (m.away, c.away)):
                votes[pair] = votes.get(pair, 0) + 1
    mapping = {}
    for (ours, theirs), _ in sorted(votes.items(), key=lambda kv: -kv[1]):
        if ours not in mapping and theirs not in mapping.values():
            mapping[ours] = theirs
    ours_left = sorted((set(matches.home) | set(matches.away)) - set(mapping))
    theirs_left = sorted((set(odds.home) | set(odds.away)) - set(mapping.values()))
    pairs = sorted(((_similar(o, t), o, t) for o in ours_left for t in theirs_left), reverse=True)
    for _, ours, theirs in pairs:
        if ours not in mapping and theirs not in mapping.values():
            mapping[ours] = theirs
    return mapping


def match_odds(matches, odds):
    """Attach odds rows to StatsBomb matches through the team name map, within three days of the
    StatsBomb date. A match is kept only when exactly one row fits and its score agrees."""
    odds = odds.dropna(subset=["date"])
    mapping = team_name_map(matches, odds)
    rows = []
    for m in matches.itertuples():
        near = abs((odds.date - pd.Timestamp(m.date)).dt.days) <= 3
        cand = odds[near & (odds.home == mapping.get(m.home)) & (odds.away == mapping.get(m.away))]
        if len(cand) != 1:
            continue
        c = cand.iloc[0]
        if (c.home_goals, c.away_goals) != (m.home_goals, m.away_goals):
            continue
        rows.append(dict(match_id=m.match_id, p_home=c.p_home, p_draw=c.p_draw, p_away=c.p_away,
                         odds_home=c.home, odds_away=c.away))
    return pd.DataFrame(rows, columns=["match_id", "p_home", "p_draw", "p_away", "odds_home", "odds_away"])
