"""Feature arrays shared by training and simulation.

Both sides call these functions, so a model always sees features built the same way. Every input
is known before the action happens. Pass length and end location are left out on purpose: StatsBomb
records where a failed pass ended, which gives away the outcome.
"""
import numpy as np

from metafut.config import (GOAL_X, GOAL_Y, HEIGHT_ID, PHASE_ID, PITCH_X, PITCH_Y, POSITION_ID,
                            RESULT_ID)

ZONES_X, ZONES_Y = 12, 8
N_ZONES = ZONES_X * ZONES_Y


def zone(x, y):
    """10 by 10 pitch zone index, 0 to 95."""
    zx = np.clip((np.asarray(x) / (PITCH_X / ZONES_X)).astype(np.int32), 0, ZONES_X - 1)
    zy = np.clip((np.asarray(y) / (PITCH_Y / ZONES_Y)).astype(np.int32), 0, ZONES_Y - 1)
    return zx + ZONES_X * zy


FINE_X, FINE_Y = 24, 16
N_FINE_ZONES = FINE_X * FINE_Y


def fine_zone(x, y):
    """5 by 5 pitch zone index, for where exact position matters."""
    zx = np.clip((np.asarray(x) / (PITCH_X / FINE_X)).astype(np.int32), 0, FINE_X - 1)
    zy = np.clip((np.asarray(y) / (PITCH_Y / FINE_Y)).astype(np.int32), 0, FINE_Y - 1)
    return zx + FINE_X * zy


def encode_table(d):
    """Add integer columns for the categorical fields of a decisions table."""
    d = d.copy()
    d["phase_id"] = d.phase.map(PHASE_ID).astype(np.int8)
    d["position_id"] = d.position.map(POSITION_ID).astype(np.int8)
    d["prev_id"] = d.prev_result.map(RESULT_ID).astype(np.int8)
    d["prev_height_id"] = d.prev_height.map(HEIGHT_ID).astype(np.int8)
    d["height_id"] = d.height.map(HEIGHT_ID).astype(np.int8)
    d["result_id"] = d.result.map(RESULT_ID).astype(np.int8)
    d["minute"] = d.t / 60.0
    return d


def _base(x, y, phase, prev, prev_same, prev_height, pressure, minute, score_diff, is_home, position):
    dist = np.hypot(GOAL_X - x, GOAL_Y - y)
    return [x, y, np.abs(y - PITCH_Y / 2), dist, phase, prev, prev_same, prev_height, pressure,
            minute, np.clip(score_diff, -3, 3), is_home, position]


ACTION_CATEGORICAL = [4, 5, 7, 12]


def action_features(x, y, phase, prev, prev_same, prev_height, pressure, minute, score_diff,
                    is_home, position):
    return np.column_stack(_base(x, y, phase, prev, prev_same, prev_height, pressure, minute,
                                 score_diff, is_home, position)).astype(np.float32)


PASS_CATEGORICAL = [4, 5, 7, 12, 16]


def pass_features(x, y, phase, prev, prev_same, prev_height, pressure, minute, score_diff,
                  is_home, position, angle, height):
    return np.column_stack(_base(x, y, phase, prev, prev_same, prev_height, pressure, minute,
                                 score_diff, is_home, position)
                           + [angle, np.cos(angle), np.abs(np.sin(angle)), height]
                           ).astype(np.float32)


SHOT_CATEGORICAL = [3, 4, 5]


def shot_features(x, y, phase, prev, prev_height, pressure):
    dist = np.hypot(GOAL_X - x, GOAL_Y - y)
    # Angle the goal mouth subtends from the shot location.
    a = np.abs(np.arctan2(GOAL_Y + 3.66 - y, GOAL_X - x) - np.arctan2(GOAL_Y - 3.66 - y, GOAL_X - x))
    return np.column_stack([dist, a, x, phase, prev, prev_height, pressure,
                            np.abs(y - PITCH_Y / 2)]).astype(np.float32)


def action_matrix(d):
    return action_features(d.x.values, d.y.values, d.phase_id.values, d.prev_id.values,
                           d.prev_same_team.values, d.prev_height_id.values, d.pressure.values,
                           d.minute.values, d.score_diff.values, d.is_home.values,
                           d.position_id.values)


def pass_matrix(d):
    return pass_features(d.x.values, d.y.values, d.phase_id.values, d.prev_id.values,
                         d.prev_same_team.values, d.prev_height_id.values, d.pressure.values,
                         d.minute.values, d.score_diff.values, d.is_home.values,
                         d.position_id.values, d.angle.values, d.height_id.values)


def shot_matrix(d):
    return shot_features(d.x.values, d.y.values, d.phase_id.values, d.prev_id.values,
                         d.prev_height_id.values, d.pressure.values)
