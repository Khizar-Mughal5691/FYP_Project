"""Who plays in each simulated match: the two teams and their starting elevens.

A fixture gives every match two team profiles and eleven player profiles per side, each with a
position group and an involvement weight (how much of the ball that player usually sees).
"""
import unicodedata
from dataclasses import dataclass

import numpy as np
import pandas as pd

from metafut.config import POSITION_ID, TABLE_DIR

XI = 11
AVERAGE_SHAPE = ["GK"] + ["DEF"] * 4 + ["MID"] * 4 + ["FWD"] * 2   # a plain 4-4-2


@dataclass
class Fixtures:
    teams: np.ndarray      # (matches, 2) team profile rows, home first
    players: np.ndarray    # (matches, 2, 11) player profile rows
    positions: np.ndarray  # (matches, 2, 11) position group ids
    weights: np.ndarray    # (matches, 2, 11) involvement weights
    labels: list = None    # optional (home, away) names per match

    @property
    def n(self):
        return len(self.teams)

    def repeat(self, k):
        """Each match k times in a row, for k rollouts of every fixture."""
        labels = None if self.labels is None else [lab for lab in self.labels for _ in range(k)]
        return Fixtures(np.repeat(self.teams, k, axis=0), np.repeat(self.players, k, axis=0),
                        np.repeat(self.positions, k, axis=0), np.repeat(self.weights, k, axis=0),
                        labels)


def _xi(profiles, player_ids, positions):
    positions = np.array([POSITION_ID[p] for p in positions], dtype=np.int64)
    rows = profiles.player_index(player_ids, positions)
    return rows, positions, profiles.player_weight[rows]


def average(n, profiles):
    """League-average teams with position-average players."""
    positions = np.array([POSITION_ID[p] for p in AVERAGE_SHAPE], dtype=np.int64)
    rows = profiles.average_player(positions)
    teams = np.full((n, 2), profiles.average_team, dtype=np.int64)
    players = np.broadcast_to(rows, (n, 2, XI)).copy()
    pos = np.broadcast_to(positions, (n, 2, XI)).copy()
    weights = np.broadcast_to(profiles.player_weight[rows], (n, 2, XI)).astype(np.float64)
    return Fixtures(teams, players, pos, weights, [("Average", "Average")] * n)


def from_lineups(profiles, lineups, home_team, away_team, home_xi, away_xi):
    """One fixture from two lists of 11 (player_id, position group) pairs."""
    sides = []
    for xi in (home_xi, away_xi):
        if len(xi) != XI:
            raise ValueError(f"a starting eleven needs {XI} players, got {len(xi)}")
        if sum(1 for _, pos in xi if pos == "GK") != 1:
            raise ValueError("a starting eleven needs exactly one goalkeeper")
        sides.append(_xi(profiles, [p for p, _ in xi], [pos for _, pos in xi]))
    teams = profiles.team_index([home_team, away_team])[None, :]
    return Fixtures(teams, np.stack([s[0] for s in sides])[None], np.stack([s[1] for s in sides])[None],
                    np.stack([s[2] for s in sides])[None].astype(np.float64), [(home_team, away_team)])


def real_matches(profiles, match_ids, lineups=None, matches=None):
    """Fixtures for real matches, with the starting elevens that really played."""
    lineups = lineups if lineups is not None else pd.read_parquet(TABLE_DIR / "lineups.parquet")
    matches = matches if matches is not None else pd.read_parquet(TABLE_DIR / "matches.parquet")
    info = matches.set_index("match_id")
    by_side = {key: g for key, g in lineups.groupby(["match_id", "team"])}
    parts = []
    for mid in match_ids:
        home, away = info.loc[mid, "home"], info.loc[mid, "away"]
        xis = [list(zip(by_side[(mid, t)].player_id, by_side[(mid, t)].position)) for t in (home, away)]
        parts.append(from_lineups(profiles, lineups, home, away, *xis))
    return concat(parts)


def usual_xi(lineups, team, match_ids):
    """The eleven who started most often for a team in the given matches: the goalkeeper with the
    most starts, then the ten outfield players with the most starts."""
    starts = lineups[(lineups.team == team) & lineups.match_id.isin(match_ids)]
    if starts.empty:
        raise KeyError(f"no lineups for {team}")
    counts = (starts.groupby("player_id")
              .agg(starts=("match_id", "nunique"), position=("position", lambda s: s.mode().iloc[0]))
              .sort_values("starts", ascending=False))
    keeper = counts[counts.position == "GK"].head(1)
    outfield = counts[counts.position != "GK"].head(XI - 1)
    xi = pd.concat([keeper, outfield])
    return list(zip(xi.index, xi.position))


def fixture(profiles, home, away, lineups=None, matches=None, split="train"):
    """A fixture between two real teams, each with its usual eleven from the given split."""
    lineups = lineups if lineups is not None else pd.read_parquet(TABLE_DIR / "lineups.parquet")
    matches = matches if matches is not None else pd.read_parquet(TABLE_DIR / "matches.parquet")
    ids = matches[matches.split == split].match_id
    home, away = find_team(profiles, home), find_team(profiles, away)
    return from_lineups(profiles, lineups, home, away,
                        usual_xi(lineups, home, ids), usual_xi(lineups, away, ids))


def _plain(text):
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


def find_team(profiles, name):
    """A team name typed by a person, matched while ignoring case and accents."""
    wanted = _plain(name)
    exact = [t for t in profiles.team_names if _plain(t) == wanted]
    if exact:
        return exact[0]
    partial = [t for t in profiles.team_names if wanted in _plain(t)]
    if len(partial) == 1:
        return partial[0]
    options = partial or profiles.team_names
    raise KeyError(f"unknown team '{name}'. Did you mean one of: {', '.join(options)}")


def concat(parts):
    return Fixtures(np.concatenate([p.teams for p in parts]), np.concatenate([p.players for p in parts]),
                    np.concatenate([p.positions for p in parts]), np.concatenate([p.weights for p in parts]),
                    [lab for p in parts for lab in (p.labels or [None] * p.n)])
