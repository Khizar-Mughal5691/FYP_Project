"""Team and player profiles, learned from training matches.

A team profile has seven numbers: how well the team keeps the ball, how often it shoots, how often
it loses the ball, the same three things for opponents playing against it, and how hard it presses.
A player profile is the share of each action in that player's decisions, plus a passing and
carrying style drawn from that player's own examples. These make Barcelona play differently from
Granada, and a winger differently from a centre-back.

Numbers based on few examples are pulled toward an average (partial pooling), so a player with
little data behaves like a typical player in the same position. Training rows get profiles
computed without their own match (leave-one-match-out), so a model cannot read a row's answer
from its own profile.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from metafut.config import ACTIONS, PHASE_ID, PITCH_X, PITCH_Y, POSITIONS
from metafut.models.features import N_ZONES, PLAYER_COLS, TEAM_ATT, TEAM_DEF, zone
from metafut.models.pools import Pool

TEAM_PRIOR = 500     # average-team decisions mixed into every team profile
PLAYER_PRIOR = 100   # position-average decisions mixed into every player profile
WEIGHT_PRIOR = 3     # position-average matches mixed into every player's involvement
STYLE_PRIOR = 30     # own passes or carries at which a player's own style counts half
PRESS_PRIOR = 200    # expected pressure events mixed into every team's pressing factor
TOUCH_PRIOR = 100    # position-average decisions mixed into every player's touch map

STYLE_X, STYLE_Y = 6, 4
N_STYLE_ZONES = STYLE_X * STYLE_Y

# Profile column -> (rows grouped by, which rows count, what counts as a hit)
TEAM_STATS = {
    "att_pass": ("team", "pass", "completed"),
    "att_shot": ("team", "all", "shot"),
    "att_loss": ("team", "all", "loss"),
    "def_pass": ("opp", "pass", "completed"),
    "def_shot": ("opp", "all", "shot"),
    "def_loss": ("opp", "all", "loss"),
    "def_press": ("opp", "open", "pressure"),
}


def style_zone(x, y):
    """20 by 20 pitch zone index, 0 to 23, used for player style."""
    zx = np.clip((np.asarray(x) / (PITCH_X / STYLE_X)).astype(np.int64), 0, STYLE_X - 1)
    zy = np.clip((np.asarray(y) / (PITCH_Y / STYLE_Y)).astype(np.int64), 0, STYLE_Y - 1)
    return zx + STYLE_X * zy


@dataclass
class Profiles:
    team_names: list
    team_att: np.ndarray        # (teams + 1, 3); the last row is an average team
    team_def: np.ndarray        # (teams + 1, 4)
    press_factor: np.ndarray    # (teams + 1,); multiplies the chance of applying pressure
    player_ids: np.ndarray      # (players,)
    player_names: list
    player_position: np.ndarray  # (players,) usual position group
    player_shares: np.ndarray   # (players + 4, 6); the last four rows are average players
    player_weight: np.ndarray   # (players + 4,) decisions per match, to choose who gets the ball
    player_touch: np.ndarray    # (players + 4, 24) share of each player's decisions per style zone
    pass_style: Pool
    pass_mix: np.ndarray        # chance of using the player's own pass style, per player and zone
    carry_style: Pool
    carry_mix: np.ndarray
    team_lookup: dict = field(init=False, repr=False)
    player_lookup: dict = field(init=False, repr=False)

    def __post_init__(self):
        self.team_lookup = {name: i for i, name in enumerate(self.team_names)}
        self.player_lookup = {int(p): i for i, p in enumerate(self.player_ids)}

    @property
    def average_team(self):
        return len(self.team_names)

    @property
    def n_players(self):
        return len(self.player_ids)

    def average_player(self, position):
        return self.n_players + np.asarray(position)

    def team_index(self, names):
        return np.array([self.team_lookup.get(n, self.average_team) for n in names], dtype=np.int64)

    def player_index(self, player_ids, positions):
        """Profile row for each player; players never seen in training get the position average."""
        idx = np.array([self.player_lookup.get(int(p), -1) for p in player_ids], dtype=np.int64)
        unseen = idx < 0
        idx[unseen] = self.average_player(np.asarray(positions, dtype=np.int64)[unseen])
        return idx


def _rows(d, which):
    if which == "pass":
        return ((d.action == "pass") & d.label_valid).to_numpy()
    if which == "open":
        return (d.phase_id == PHASE_ID["open"]).to_numpy()
    return np.ones(len(d), dtype=bool)


def _hits(d, what):
    if what == "completed":
        return (d.result == "pass_complete").to_numpy()
    if what == "pressure":
        return (d.pressure == 1).to_numpy()
    return (d.action == what).to_numpy()


def _shrink(hits, counts, mean, prior):
    return (hits + prior * mean) / (counts + prior)


def _lookup(series, keys, fill=0.0):
    return series.reindex(keys).fillna(fill).to_numpy(dtype=np.float64)


def _team_stat(tr, by, which, what):
    """Totals per team and per team and match, for one profile number."""
    sel = _rows(tr, which)
    hits = pd.Series(_hits(tr, what)[sel].astype(np.float64))
    keys = tr[by].to_numpy()[sel]
    matches = tr.match_id.to_numpy()[sel]
    total = hits.groupby(keys).agg(["sum", "count"])
    per_match = hits.groupby([keys, matches]).agg(["sum", "count"])
    return total, per_match, float(hits.mean())


def _team_profiles(tr, team_names):
    """Profile per team for simulation, and leave-one-match-out values for training rows."""
    full = np.zeros((len(team_names) + 1, len(TEAM_STATS)))
    loo = {}
    for j, (col, (by, which, what)) in enumerate(TEAM_STATS.items()):
        total, per_match, mean = _team_stat(tr, by, which, what)
        full[:-1, j] = _shrink(_lookup(total["sum"], team_names), _lookup(total["count"], team_names),
                               mean, TEAM_PRIOR)
        full[-1, j] = mean
        keys = tr[by].to_numpy()
        own = pd.MultiIndex.from_arrays([keys, tr.match_id.to_numpy()])
        hits = _lookup(total["sum"], keys) - _lookup(per_match["sum"], own)
        counts = _lookup(total["count"], keys) - _lookup(per_match["count"], own)
        loo[col] = _shrink(hits, counts, mean, TEAM_PRIOR)
    n_att = len(TEAM_ATT)
    return full[:, :n_att], full[:, n_att:], loo


def _player_profiles(tr):
    """Action shares, usual position and involvement for every player in the training rows."""
    action = pd.Categorical(tr.action, categories=ACTIONS)
    per_match = pd.crosstab([tr.player_id, tr.match_id], action).reindex(columns=ACTIONS, fill_value=0)
    total = per_match.groupby(level=0).sum()

    prior = (pd.crosstab(tr.position_id, action, normalize="index")
             .reindex(index=range(len(POSITIONS)), columns=ACTIONS, fill_value=0).to_numpy())
    player_ids = total.index.to_numpy()
    usual = (tr.groupby("player_id").position_id.agg(lambda s: s.value_counts().index[0])
             .reindex(player_ids).to_numpy(dtype=np.int64))
    names = tr.groupby("player_id").player.first().reindex(player_ids).tolist()

    counts = total.to_numpy(dtype=np.float64)
    n = counts.sum(axis=1, keepdims=True)
    shares = (counts + PLAYER_PRIOR * prior[usual]) / (n + PLAYER_PRIOR)
    shares = np.vstack([shares, prior])

    # Involvement: decisions per match played, pulled toward the position average.
    matches = per_match.groupby(level=0).size().reindex(player_ids).to_numpy(dtype=np.float64)
    decisions = n[:, 0]
    group_rate = np.array([decisions[usual == g].sum() / max(matches[usual == g].sum(), 1)
                           for g in range(len(POSITIONS))])
    weight = (decisions + WEIGHT_PRIOR * group_rate[usual]) / (matches + WEIGHT_PRIOR)
    weight = np.concatenate([weight, group_rate])

    # Touch map: where on the pitch each player makes decisions. A centre-back and a full-back are
    # both defenders, but only one of them is usually on the ball in the middle of his own box.
    zones = pd.Categorical(style_zone(tr.x.to_numpy(), tr.y.to_numpy()), categories=range(N_STYLE_ZONES))
    by_player = pd.crosstab(tr.player_id, zones).reindex(index=player_ids, columns=range(N_STYLE_ZONES),
                                                         fill_value=0).to_numpy(dtype=np.float64)
    touch_prior = (pd.crosstab(tr.position_id, zones, normalize="index")
                   .reindex(index=range(len(POSITIONS)), columns=range(N_STYLE_ZONES), fill_value=0)
                   .to_numpy())
    touch = (by_player + TOUCH_PRIOR * touch_prior[usual]) / (by_player.sum(axis=1, keepdims=True) + TOUCH_PRIOR)
    touch = np.vstack([touch, touch_prior])

    # Leave-one-match-out shares for the training rows.
    rows = pd.MultiIndex.from_arrays([tr.player_id.to_numpy(), tr.match_id.to_numpy()])
    own = per_match.reindex(rows, fill_value=0).to_numpy(dtype=np.float64)
    rest = total.reindex(tr.player_id.to_numpy(), fill_value=0).to_numpy(dtype=np.float64) - own
    row_prior = prior[tr.position_id.to_numpy()]
    loo = (rest + PLAYER_PRIOR * row_prior) / (rest.sum(axis=1, keepdims=True) + PLAYER_PRIOR)
    return player_ids, names, usual, shares, weight, touch, loo


def _style_pool(rows, values, player_lookup, n_players):
    keys = (rows.player_id.map(player_lookup).to_numpy(dtype=np.int64) * N_STYLE_ZONES
            + style_zone(rows.x.to_numpy(), rows.y.to_numpy()))
    pool = Pool(keys, values, n_players * N_STYLE_ZONES, min_count=1)
    mix = (pool.count / (pool.count + STYLE_PRIOR)).astype(np.float32)
    return pool, mix


def build_profiles(tr):
    """Profiles from the training rows. Returns the profiles and the training rows with
    leave-one-match-out profile columns added."""
    tr = tr.copy()
    team_names = sorted(set(tr.team) | set(tr.opp))
    team_att, team_def, team_loo = _team_profiles(tr, team_names)
    player_ids, names, usual, shares, weight, touch, player_loo = _player_profiles(tr)
    lookup = {int(p): i for i, p in enumerate(player_ids)}

    passes = tr[(tr.action == "pass") & (tr.phase_id == PHASE_ID["open"])]
    pass_style, pass_mix = _style_pool(passes, np.column_stack([passes.height_id, passes.angle]),
                                       lookup, len(player_ids))
    carries = tr[tr.action == "carry"]
    carry_style, carry_mix = _style_pool(
        carries, np.column_stack([carries.end_x - carries.x, carries.end_y - carries.y]),
        lookup, len(player_ids))

    profiles = Profiles(team_names, team_att, team_def, np.ones(len(team_names) + 1),
                        player_ids, names, usual, shares, weight, touch,
                        pass_style, pass_mix, carry_style, carry_mix)
    for col, values in team_loo.items():
        tr[col] = values
    tr[PLAYER_COLS] = player_loo
    return profiles, tr


def attach(profiles, frame):
    """Add profile columns to rows outside training, using the full training profiles."""
    frame = frame.copy()
    own = profiles.team_index(frame.team)
    opp = profiles.team_index(frame.opp)
    frame[TEAM_ATT] = profiles.team_att[own]
    frame[TEAM_DEF] = profiles.team_def[opp]
    frame[PLAYER_COLS] = profiles.player_shares[profiles.player_index(frame.player_id, frame.position_id)]
    return frame


def pressing_factor(tr, pressure_table, profiles, key):
    """How much more or less often each team presses than the situation predicts. `key` builds
    the pressure table's key from (prev, x, y, position)."""
    o = tr[tr.phase_id == PHASE_ID["open"]]
    expected = pressure_table[key(o.prev_id.to_numpy(), o.x.to_numpy(), o.y.to_numpy(), o.position_id.to_numpy())]
    by_team = pd.DataFrame({"opp": o.opp.to_numpy(), "obs": o.pressure.to_numpy(), "exp": expected})
    sums = by_team.groupby("opp")[["obs", "exp"]].sum()
    factor = ((sums.obs + PRESS_PRIOR) / (sums.exp + PRESS_PRIOR)).reindex(profiles.team_names).fillna(1.0)
    return np.concatenate([factor.to_numpy(), [1.0]])
