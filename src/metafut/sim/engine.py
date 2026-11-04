"""Event-driven match simulator. Many matches advance together, one decision per step.

Every array below holds one value per match still running, so one model call serves all of them.
That is what makes 1,000 rollouts practical: calling a model row by row would take far longer.

One step: read the state, draw pressure, choose an action, resolve its outcome, then draw what
happens next from real examples of the same situation.
"""
from dataclasses import dataclass, field

import joblib
import numpy as np

from metafut.config import ACTION_ID, MODEL_DIR, PHASE_ID, PITCH_X, PITCH_Y, POSITION_ID, RESULT_ID
from metafut.models.features import N_ZONES, action_features, pass_features, shot_features, zone
from metafut.models.train import octant, pass_length_keys, pass_shape_key, transition_key

HALF_SECONDS = 45 * 60
A_PASS, A_CARRY, A_DRIBBLE, A_SHOT = (ACTION_ID[a] for a in ("pass", "carry", "dribble", "shot"))
A_LOSS, A_CLEAR = ACTION_ID["loss"], ACTION_ID["clear"]
OPEN = PHASE_ID["open"]
PENALTY = PHASE_ID["penalty"]
FORCED_PASS = [PHASE_ID[p] for p in ("kick_off", "throw_in", "goal_kick", "corner")]
MAX_REDRAWS = 5


def on_pitch(x, y):
    return (x >= 0) & (x <= PITCH_X) & (y >= 0) & (y <= PITCH_Y)


@dataclass
class SimResult:
    """Totals per match and per team: arrays of shape (matches, 2), home first."""
    goals: np.ndarray
    shots: np.ndarray
    xg: np.ndarray
    passes: np.ndarray
    completed: np.ndarray
    carries: np.ndarray
    dribbles: np.ndarray
    decisions: np.ndarray
    ball_seconds: np.ndarray
    events: list = field(default_factory=list)
    # One row per shot: match, team, x, y, phase, previous result, goal probability, scored.
    shot_log: np.ndarray = None


class Simulator:
    def __init__(self, bundle=None):
        b = bundle or joblib.load(MODEL_DIR / "simulator_v0.joblib")
        self.pass_model = b["pass_model"]
        self.action_model = b["action_model"]
        self.shot_model = b["shot_model"]
        self.pools = b["pools"]
        self.tables = b["tables"]

    def run(self, n=1000, seed=0, record_first=False):
        rng = np.random.default_rng(seed)
        ends = self.tables["half_end"][rng.integers(0, len(self.tables["half_end"]), n)]

        # State of every match. team 0 is home, team 1 is away.
        kickoff = rng.integers(0, 2, n)
        team, x, y = kickoff.copy(), np.full(n, 60.0), np.full(n, 40.0)
        phase = np.full(n, PHASE_ID["kick_off"], dtype=np.int64)
        prev = np.full(n, RESULT_ID["start"], dtype=np.int64)
        prev_same = np.zeros(n, dtype=np.int64)
        prev_height = np.zeros(n, dtype=np.int64)
        position = np.full(n, POSITION_ID["MID"], dtype=np.int64)
        period = np.ones(n, dtype=np.int64)
        t = np.zeros(n)

        goals, shots, passes, completed = (np.zeros((n, 2), dtype=np.int32) for _ in range(4))
        carries, dribbles, decisions = (np.zeros((n, 2), dtype=np.int32) for _ in range(3))
        xg_total, ball_seconds = np.zeros((n, 2)), np.zeros((n, 2))
        events, shot_rows = [], []

        running = np.arange(n)
        while running.size:
            i = running
            m = i.size
            tm, px, py, ph, pv = team[i], x[i], y[i], phase[i], prev[i]
            z = zone(px, py)

            # Pressure, then the action this player chooses.
            pressure = (rng.random(m) < self.tables["pressure"][pv * N_ZONES + z]).astype(np.int64)
            pressure[ph != OPEN] = 0
            score_diff = goals[i, tm] - goals[i, 1 - tm]
            is_home = (tm == 0).astype(np.int64)
            minute = t[i] / 60.0
            probs = self.action_model.predict_proba(action_features(
                px, py, ph, pv, prev_same[i], prev_height[i], pressure, minute, score_diff,
                is_home, position[i]))
            action = (rng.random((m, 1)) < np.cumsum(probs, axis=1)).argmax(axis=1)
            action[np.isin(ph, FORCED_PASS)] = A_PASS
            action[ph == PENALTY] = A_SHOT

            result = np.full(m, RESULT_ID["loss"], dtype=np.int64)
            result[action == A_CLEAR] = RESULT_ID["clear"]
            end_x, end_y = px.copy(), py.copy()
            height_now = np.zeros(m, dtype=np.int64)

            # Pass: draw height and direction, ask the pass model, then draw how far it went.
            s = np.flatnonzero(action == A_PASS)
            if s.size:
                keys = pass_shape_key(ph[s], z[s], position[i][s])
                shape = self.pools["pass_shape"].sample(keys, rng, fallbacks=[ph[s]])
                h, angle = shape[:, 0].astype(np.int64), shape[:, 1]
                p_ok = self.pass_model.predict_proba(pass_features(
                    px[s], py[s], ph[s], pv[s], prev_same[i][s], prev_height[i][s], pressure[s],
                    minute[s], score_diff[s], is_home[s], position[i][s], angle, h))[:, 1]
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
                np.add.at(passes, (i[s], tm[s]), 1)
                np.add.at(completed, (i[s], tm[s]), 1 - failed)

            s = np.flatnonzero(action == A_CARRY)
            if s.size:
                keys = z[s] * len(POSITION_ID) + position[i][s]
                d = self.pools["carry"].sample(keys, rng)
                for _ in range(MAX_REDRAWS):
                    bad = np.flatnonzero(~on_pitch(px[s] + d[:, 0], py[s] + d[:, 1]))
                    if not bad.size:
                        break
                    d[bad] = self.pools["carry"].sample(keys[bad], rng)
                end_x[s] = px[s] + d[:, 0]
                end_y[s] = py[s] + d[:, 1]
                result[s] = RESULT_ID["carry"]
                np.add.at(carries, (i[s], tm[s]), 1)

            s = np.flatnonzero(action == A_DRIBBLE)
            if s.size:
                ok = rng.random(s.size) < self.tables["dribble"][z[s] * 2 + pressure[s]]
                result[s] = np.where(ok, RESULT_ID["dribble_success"], RESULT_ID["dribble_fail"])
                np.add.at(dribbles, (i[s], tm[s]), 1)

            s = np.flatnonzero(action == A_SHOT)
            if s.size:
                p_goal = self.shot_model.predict_proba(shot_features(
                    px[s], py[s], ph[s], pv[s], prev_height[i][s], pressure[s]))[:, 1]
                scored = rng.random(s.size) < p_goal
                result[s] = np.where(scored, RESULT_ID["shot_goal"], RESULT_ID["shot_nogoal"])
                np.add.at(shots, (i[s], tm[s]), 1)
                np.add.at(xg_total, (i[s], tm[s]), p_goal)
                np.add.at(goals, (i[s[scored]], tm[s[scored]]), 1)
                shot_rows.append(np.column_stack([i[s], tm[s], px[s], py[s], ph[s], pv[s], p_goal, scored]))

            np.add.at(decisions, (i, tm), 1)
            end_x, end_y = np.clip(end_x, 0, PITCH_X), np.clip(end_y, 0, PITCH_Y)

            # What happens next: a real example of what followed this result in this zone.
            nxt = self.pools["next"].sample(transition_key(result, zone(end_x, end_y)), rng,
                                            fallbacks=[result])
            same = nxt[:, 0].astype(np.int64)
            next_phase = nxt[:, 5].astype(np.int64)
            base_x = np.where(same == 1, end_x, PITCH_X - end_x)
            base_y = np.where(same == 1, end_y, PITCH_Y - end_y)
            moved_x, moved_y = base_x + nxt[:, 1], base_y + nxt[:, 2]
            inside = on_pitch(moved_x, moved_y)
            moved_x, moved_y = np.where(inside, moved_x, base_x), np.where(inside, moved_y, base_y)
            next_x = np.where(next_phase == OPEN, moved_x, nxt[:, 3])
            next_y = np.where(next_phase == OPEN, moved_y, nxt[:, 4])
            next_position = nxt[:, 6].astype(np.int64)

            goal = result == RESULT_ID["shot_goal"]
            same[goal], next_phase[goal], next_position[goal] = 0, PHASE_ID["kick_off"], POSITION_ID["MID"]
            next_x[goal], next_y[goal] = 60.0, 40.0

            dt = nxt[:, 7]
            np.add.at(ball_seconds, (i, tm), dt)
            if record_first and i[0] == 0:
                events.append(dict(t=float(t[0]), team=int(tm[0]), x=float(px[0]), y=float(py[0]),
                                   end_x=float(end_x[0]), end_y=float(end_y[0]),
                                   action=int(action[0]), result=int(result[0]),
                                   position=int(position[0]), pressure=int(pressure[0])))

            team[i] = np.where(same == 1, tm, 1 - tm)
            x[i], y[i] = np.clip(next_x, 0, PITCH_X), np.clip(next_y, 0, PITCH_Y)
            phase[i], prev[i], prev_same[i] = next_phase, result, same
            prev_height[i] = np.where(result == RESULT_ID["pass_complete"], height_now, 0)
            position[i] = next_position
            t[i] += dt

            # Half-time and full-time.
            over = t[i] >= ends[i, period[i] - 1]
            first = i[over & (period[i] == 1)]
            finished = over & (period[i] == 2)
            if first.size:
                period[first], t[first] = 2, HALF_SECONDS
                team[first] = 1 - kickoff[first]
                x[first], y[first], phase[first] = 60.0, 40.0, PHASE_ID["kick_off"]
                prev[first], prev_same[first], prev_height[first] = RESULT_ID["start"], 0, 0
                position[first] = POSITION_ID["MID"]
            running = i[~finished]

        shot_log = np.vstack(shot_rows) if shot_rows else np.empty((0, 8))
        return SimResult(goals, shots, xg_total, passes, completed, carries, dribbles, decisions,
                         ball_seconds, events, shot_log)


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
