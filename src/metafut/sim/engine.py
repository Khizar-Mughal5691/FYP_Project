"""Event-driven match simulator. Many matches advance together, one decision per step.

Every array below holds one value per match still running, so one model call serves all of them.
That is what makes 1,000 rollouts practical: calling a model row by row would take far longer.

One step: read the state, draw pressure, let the player on the ball choose an action, resolve its
outcome, then draw what happens next from real examples of the same situation and decide which
player has the ball. The two teams and their elevens come from a Fixtures object; each team and
player brings its own profile (see models/profiles.py).
"""
from dataclasses import dataclass, field

import joblib
import numpy as np

from metafut.config import (ACTION_ID, BUNDLE, MODEL_DIR, PHASE_ID, PITCH_X, PITCH_Y, POSITION_ID,
                            POSITIONS, RESULT_ID)
from metafut.models.fast_predict import FastHGB
from metafut.models.features import (N_ZONES, PASS_PROFILE, TEAM_ATT, TEAM_DEF, action_features,
                                     pass_features, shot_features, zone)
from metafut.models.profiles import N_STYLE_ZONES, style_zone
from metafut.models.train import (carry_keys, octant, pass_length_keys, pass_shape_keys, pressure_key,
                                  transition_keys)
from metafut.sim import fixtures as fixture_tools

HALF_SECONDS = 45 * 60
A_PASS, A_CARRY, A_DRIBBLE, A_SHOT = (ACTION_ID[a] for a in ("pass", "carry", "dribble", "shot"))
A_LOSS, A_CLEAR = ACTION_ID["loss"], ACTION_ID["clear"]
OPEN = PHASE_ID["open"]
PENALTY = PHASE_ID["penalty"]
KICK_OFF = PHASE_ID["kick_off"]
FORCED_PASS = [PHASE_ID[p] for p in ("kick_off", "throw_in", "goal_kick", "corner")]
GK = POSITION_ID["GK"]
MAX_REDRAWS = 5
MAX_PRESSURE = 0.95
# Where each PASS_PROFILE column comes from in the team profiles.
PASS_FROM = [("att", TEAM_ATT.index(c)) if c in TEAM_ATT else ("def", TEAM_DEF.index(c))
             for c in PASS_PROFILE]


def on_pitch(x, y):
    return (x >= 0) & (x <= PITCH_X) & (y >= 0) & (y <= PITCH_Y)


def receiver_weights(profiles, players, weights, x, y):
    """How likely each of the eleven is to be on the ball at (x, y): how much of the ball the
    player usually sees, times how often the player is in that part of the pitch."""
    z = style_zone(np.clip(x, 0, PITCH_X), np.clip(y, 0, PITCH_Y))
    return weights * profiles.player_touch[players, z[:, None]]


def choose_players(rng, positions, weights, group, exclude=None):
    """One player per row, from the wanted position group, in proportion to `weights`.
    `exclude` gives a slot per row that cannot be chosen (-1 for none). If the group has nobody
    available, any outfield player can be chosen."""
    m = len(group)
    exclude = np.full(m, -1) if exclude is None else np.asarray(exclude)
    w = weights * (positions == np.asarray(group)[:, None])
    blocked = np.flatnonzero(exclude >= 0)
    w[blocked, exclude[blocked]] = 0
    empty = w.sum(axis=1) <= 0
    if empty.any():
        w[empty] = weights[empty] * (positions[empty] != GK)
        again = np.flatnonzero(empty & (exclude >= 0))
        w[again, exclude[again]] = 0
    cum = np.cumsum(w, axis=1)
    u = rng.random(m) * cum[:, -1]
    return (u[:, None] < cum).argmax(axis=1)


@dataclass
class SimResult:
    """Totals per match and team, arrays of shape (matches, 2) with home first. The player_*
    arrays have shape (matches, 2, 11), one value per starting player."""
    goals: np.ndarray
    shots: np.ndarray
    xg: np.ndarray
    passes: np.ndarray
    completed: np.ndarray
    carries: np.ndarray
    dribbles: np.ndarray
    decisions: np.ndarray
    ball_seconds: np.ndarray
    player_goals: np.ndarray
    player_shots: np.ndarray
    player_xg: np.ndarray
    player_passes: np.ndarray
    player_decisions: np.ndarray
    fixtures: object = None
    events: list = field(default_factory=list)
    # One row per shot: match, team, x, y, phase, previous result, goal probability, scored, slot.
    shot_log: np.ndarray = None
    # With trace=True: every decision of every match, one array per TRACE_COLUMNS name.
    trace: dict = None


TRACE_COLUMNS = ["match", "team", "slot", "t", "x", "y", "end_x", "end_y", "phase", "prev",
                 "pressure", "action", "result"]


class Simulator:
    def __init__(self, bundle=None):
        b = bundle or joblib.load(MODEL_DIR / BUNDLE)
        # Same predictions as the fitted models, with less overhead per call (models/fast_predict.py).
        self.pass_model = FastHGB(b["pass_model"])
        self.action_model = FastHGB(b["action_model"])
        self.shot_model = FastHGB(b["shot_model"])
        self.pools = b["pools"]
        self.tables = b["tables"]
        self.profiles = b["profiles"]

    def run(self, n=1000, seed=0, fixtures=None, record_first=False, trace=False):
        """Simulate matches. Without fixtures, n league-average matches; with fixtures, one match
        per fixture row (use Fixtures.repeat for several rollouts of the same fixture).
        record_first keeps a readable event list for the first match; trace keeps every
        decision of every match (memory grows with the number of matches)."""
        P = self.profiles
        fx = fixtures if fixtures is not None else fixture_tools.average(n, P)
        n = fx.n
        rng = np.random.default_rng(seed)
        ends = self.tables["half_end"][rng.integers(0, len(self.tables["half_end"]), n)]
        kickoff_groups = self.tables["kickoff_position"]

        # State of every match. Side 0 is home, side 1 is away; slot is the player on the ball.
        team = np.zeros(n, dtype=np.int64)
        slot = np.zeros(n, dtype=np.int64)
        x, y = np.full(n, 60.0), np.full(n, 40.0)
        phase = np.full(n, KICK_OFF, dtype=np.int64)
        prev = np.full(n, RESULT_ID["start"], dtype=np.int64)
        prev_same = np.zeros(n, dtype=np.int64)
        prev_height = np.zeros(n, dtype=np.int64)
        period = np.ones(n, dtype=np.int64)
        t = np.zeros(n)

        def kick_off(rows, side):
            team[rows] = side
            x[rows], y[rows], phase[rows] = 60.0, 40.0, KICK_OFF
            prev[rows], prev_same[rows], prev_height[rows] = RESULT_ID["start"], 0, 0
            group = rng.choice(len(POSITIONS), size=rows.size, p=kickoff_groups)
            w = receiver_weights(P, fx.players[rows, side], fx.weights[rows, side], x[rows], y[rows])
            slot[rows] = choose_players(rng, fx.positions[rows, side], w, group)

        first_kick = rng.integers(0, 2, n)
        kick_off(np.arange(n), first_kick)

        totals = {k: np.zeros((n, 2), dtype=np.int32)
                  for k in ("goals", "shots", "passes", "completed", "carries", "dribbles", "decisions")}
        xg_total, ball_seconds = np.zeros((n, 2)), np.zeros((n, 2))
        per_player = {k: np.zeros((n, 2, fixture_tools.XI)) for k in ("goals", "shots", "xg", "passes", "decisions")}
        events, shot_rows, trace_rows = [], [], []

        running = np.arange(n)
        while running.size:
            i = running
            m = i.size
            tm, sl, px, py, ph, pv = team[i], slot[i], x[i], y[i], phase[i], prev[i]
            own, opp = fx.teams[i, tm], fx.teams[i, 1 - tm]
            pid = fx.players[i, tm, sl]
            position = fx.positions[i, tm, sl]
            z = zone(px, py)

            # Pressure depends on the situation and on how hard the defending team presses.
            p_press = np.minimum(self.tables["pressure"][pressure_key(pv, px, py, position)] * P.press_factor[opp],
                                 MAX_PRESSURE)
            pressure = (rng.random(m) < p_press).astype(np.int64)
            pressure[ph != OPEN] = 0
            score_diff = totals["goals"][i, tm] - totals["goals"][i, 1 - tm]
            is_home = (tm == 0).astype(np.int64)
            minute = t[i] / 60.0

            # The player on the ball chooses an action.
            profile = np.hstack([P.team_att[own], P.team_def[opp], P.player_shares[pid]])
            probs = self.action_model.predict_proba(action_features(
                px, py, ph, pv, prev_same[i], prev_height[i], pressure, minute, score_diff,
                is_home, position, profile))
            probs[:, A_SHOT] *= self.tables.get("shot_scale", 1.0)   # see sim/calibrate.py
            probs /= probs.sum(axis=1, keepdims=True)
            action = (rng.random((m, 1)) < np.cumsum(probs, axis=1)).argmax(axis=1)
            action[np.isin(ph, FORCED_PASS)] = A_PASS
            action[ph == PENALTY] = A_SHOT

            result = np.full(m, RESULT_ID["loss"], dtype=np.int64)
            result[action == A_CLEAR] = RESULT_ID["clear"]
            end_x, end_y = px.copy(), py.copy()
            height_now = np.zeros(m, dtype=np.int64)
            own_style = (pid < P.n_players) & (ph == OPEN)

            # Pass: draw height and direction (from the player's own style where there is enough
            # of it), ask the pass model, then draw where it ends.
            s = np.flatnonzero(action == A_PASS)
            if s.size:
                keys, coarser = pass_shape_keys(ph[s], px[s], py[s], position[s])
                shape = self.pools["pass_shape"].sample(keys, rng, fallbacks=coarser)
                self._own_style(rng, shape, s, own_style, pid, px, py, P.pass_style, P.pass_mix)
                h, angle = shape[:, 0].astype(np.int64), shape[:, 1]
                team_cols = {"att": P.team_att[own[s]], "def": P.team_def[opp[s]]}
                pass_profile = np.column_stack([team_cols[side][:, j] for side, j in PASS_FROM])
                p_ok = self.pass_model.predict_proba(pass_features(
                    px[s], py[s], ph[s], pv[s], prev_same[i][s], prev_height[i][s], pressure[s],
                    minute[s], score_diff[s], is_home[s], position[s], angle, h, pass_profile))[:, 1]
                failed = (rng.random(s.size) >= p_ok).astype(np.int64)
                keys, coarser = pass_length_keys(ph[s], px[s], py[s], h, octant(angle), failed)
                drawn = self.pools["pass_length"].sample(keys, rng, fallbacks=coarser)
                # A completed pass stays on the pitch, so redraw any that would land outside.
                for _ in range(MAX_REDRAWS):
                    bad = np.flatnonzero((failed == 0) & ~on_pitch(px[s] + drawn[:, 0], py[s] + drawn[:, 1]))
                    if not bad.size:
                        break
                    drawn[bad] = self.pools["pass_length"].sample(keys[bad], rng,
                                                                  fallbacks=[c[bad] for c in coarser])
                end_x[s] = px[s] + drawn[:, 0]
                end_y[s] = py[s] + drawn[:, 1]
                result[s] = drawn[:, 2].astype(np.int64)
                result[s[failed == 0]] = RESULT_ID["pass_complete"]
                result[s[(failed == 1) & (result[s] == RESULT_ID["pass_complete"])]] = RESULT_ID["pass_incomplete"]
                height_now[s] = h
                np.add.at(totals["passes"], (i[s], tm[s]), 1)
                np.add.at(totals["completed"], (i[s], tm[s]), 1 - failed)
                np.add.at(per_player["passes"], (i[s], tm[s], sl[s]), 1)

            s = np.flatnonzero(action == A_CARRY)
            if s.size:
                keys, coarser = carry_keys(px[s], py[s], position[s])
                d = self.pools["carry"].sample(keys, rng, fallbacks=coarser)
                self._own_style(rng, d, s, own_style, pid, px, py, P.carry_style, P.carry_mix)
                for _ in range(MAX_REDRAWS):
                    bad = np.flatnonzero(~on_pitch(px[s] + d[:, 0], py[s] + d[:, 1]))
                    if not bad.size:
                        break
                    d[bad] = self.pools["carry"].sample(keys[bad], rng, fallbacks=[c[bad] for c in coarser])
                end_x[s] = px[s] + d[:, 0]
                end_y[s] = py[s] + d[:, 1]
                result[s] = RESULT_ID["carry"]
                np.add.at(totals["carries"], (i[s], tm[s]), 1)

            s = np.flatnonzero(action == A_DRIBBLE)
            if s.size:
                ok = rng.random(s.size) < self.tables["dribble"][z[s] * 2 + pressure[s]]
                result[s] = np.where(ok, RESULT_ID["dribble_success"], RESULT_ID["dribble_fail"])
                np.add.at(totals["dribbles"], (i[s], tm[s]), 1)

            s = np.flatnonzero(action == A_SHOT)
            if s.size:
                p_goal = self.shot_model.predict_proba(shot_features(
                    px[s], py[s], ph[s], pv[s], prev_height[i][s], pressure[s]))[:, 1]
                scored = rng.random(s.size) < p_goal
                result[s] = np.where(scored, RESULT_ID["shot_goal"], RESULT_ID["shot_nogoal"])
                np.add.at(totals["shots"], (i[s], tm[s]), 1)
                np.add.at(xg_total, (i[s], tm[s]), p_goal)
                np.add.at(totals["goals"], (i[s[scored]], tm[s[scored]]), 1)
                np.add.at(per_player["shots"], (i[s], tm[s], sl[s]), 1)
                np.add.at(per_player["xg"], (i[s], tm[s], sl[s]), p_goal)
                np.add.at(per_player["goals"], (i[s[scored]], tm[s[scored]], sl[s[scored]]), 1)
                shot_rows.append(np.column_stack([i[s], tm[s], px[s], py[s], ph[s], pv[s], p_goal,
                                                  scored, sl[s]]))

            np.add.at(totals["decisions"], (i, tm), 1)
            np.add.at(per_player["decisions"], (i, tm, sl), 1)
            end_x, end_y = np.clip(end_x, 0, PITCH_X), np.clip(end_y, 0, PITCH_Y)

            # What happens next: a real example of what followed this result in this zone.
            keys, coarser = transition_keys(result, end_x, end_y)
            nxt = self.pools["next"].sample(keys, rng, fallbacks=coarser)
            same = nxt[:, 0].astype(np.int64)
            same_player = nxt[:, 8].astype(np.int64) * same
            next_phase = nxt[:, 5].astype(np.int64)
            base_x = np.where(same == 1, end_x, PITCH_X - end_x)
            base_y = np.where(same == 1, end_y, PITCH_Y - end_y)
            moved_x, moved_y = base_x + nxt[:, 1], base_y + nxt[:, 2]
            inside = on_pitch(moved_x, moved_y)
            moved_x, moved_y = np.where(inside, moved_x, base_x), np.where(inside, moved_y, base_y)
            next_x = np.where(next_phase == OPEN, moved_x, nxt[:, 3])
            next_y = np.where(next_phase == OPEN, moved_y, nxt[:, 4])
            next_group = nxt[:, 6].astype(np.int64)

            goal = result == RESULT_ID["shot_goal"]
            same[goal], same_player[goal], next_phase[goal] = 0, 0, KICK_OFF
            next_x[goal], next_y[goal] = 60.0, 40.0
            if goal.any():
                next_group[goal] = rng.choice(len(POSITIONS), size=goal.sum(), p=kickoff_groups)

            # Who has the ball next: the same player again, a teammate or an opponent.
            side = np.where(same == 1, tm, 1 - tm)
            next_slot = sl.copy()
            r = np.flatnonzero(same_player == 0)
            if r.size:
                exclude = np.where(same[r] == 1, sl[r], -1)
                w = receiver_weights(P, fx.players[i[r], side[r]], fx.weights[i[r], side[r]],
                                     next_x[r], next_y[r])
                next_slot[r] = choose_players(rng, fx.positions[i[r], side[r]], w, next_group[r], exclude)

            dt = nxt[:, 7]
            np.add.at(ball_seconds, (i, tm), dt)
            if trace:
                trace_rows.append(np.column_stack([i, tm, sl, t[i], px, py, end_x, end_y, ph, pv,
                                                   pressure, action, result]).astype(np.float32))
            if record_first and i[0] == 0:
                events.append(dict(t=float(t[0]), team=int(tm[0]), slot=int(sl[0]), player=int(pid[0]),
                                   x=float(px[0]), y=float(py[0]), end_x=float(end_x[0]),
                                   end_y=float(end_y[0]), action=int(action[0]), result=int(result[0]),
                                   position=int(position[0]), pressure=int(pressure[0])))

            team[i], slot[i] = side, next_slot
            x[i], y[i] = np.clip(next_x, 0, PITCH_X), np.clip(next_y, 0, PITCH_Y)
            phase[i], prev[i], prev_same[i] = next_phase, result, same
            prev_height[i] = np.where(result == RESULT_ID["pass_complete"], height_now, 0)
            t[i] += dt

            # Half-time and full-time.
            over = t[i] >= ends[i, period[i] - 1]
            first = i[over & (period[i] == 1)]
            finished = over & (period[i] == 2)
            if first.size:
                period[first], t[first] = 2, HALF_SECONDS
                kick_off(first, 1 - first_kick[first])
            running = i[~finished]

        shot_log = np.vstack(shot_rows) if shot_rows else np.empty((0, 9))
        traced = None
        if trace:
            stacked = np.vstack(trace_rows)
            traced = {c: stacked[:, j] for j, c in enumerate(TRACE_COLUMNS)}
        return SimResult(totals["goals"], totals["shots"], xg_total, totals["passes"], totals["completed"],
                         totals["carries"], totals["dribbles"], totals["decisions"], ball_seconds,
                         per_player["goals"], per_player["shots"], per_player["xg"],
                         per_player["passes"], per_player["decisions"], fx, events, shot_log, traced)

    @staticmethod
    def _own_style(rng, drawn, s, own_style, pid, px, py, style_pool, mix):
        """Replace some draws with draws from the player's own examples. The more examples a
        player has in this part of the pitch, the more often their own style is used."""
        cand = np.flatnonzero(own_style[s])
        if not cand.size:
            return
        rows = s[cand]
        keys = pid[rows] * N_STYLE_ZONES + style_zone(px[rows], py[rows])
        use = rng.random(cand.size) < mix[keys]
        if use.any():
            drawn[cand[use]] = style_pool.sample(keys[use], rng)


def summary(r):
    """Per-match averages from a simulation, on the same footing as real_targets."""
    g = r.goals
    return dict(
        matches=int(len(g)), goals=float(g.sum(1).mean()), shots=float(r.shots.sum(1).mean()),
        xg=float(r.xg.sum(1).mean()), passes=float(r.passes.sum(1).mean()),
        completion=float(r.completed.sum() / max(r.passes.sum(), 1)),
        carries=float(r.carries.sum(1).mean()), dribbles=float(r.dribbles.sum(1).mean()),
        decisions=float(r.decisions.sum(1).mean()), home_win=float((g[:, 0] > g[:, 1]).mean()),
        draw=float((g[:, 0] == g[:, 1]).mean()), away_win=float((g[:, 0] < g[:, 1]).mean()))


def player_name(profiles, row):
    """Display name of a profile row; average players are named by position."""
    if row < profiles.n_players:
        return profiles.player_names[row]
    return f"Average {POSITIONS[row - profiles.n_players]}"
