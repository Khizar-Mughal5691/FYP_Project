"""Train everything the simulator needs and report results on validation matches.

The test split is never read here. Final models are fitted on the train split only, so the
validation scores stay honest; refitting on train + val happens once, before the final evaluation.
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from metafut.config import (ACTION_ID, ACTIONS, BUNDLE, HEIGHT_ID, LEAGUES, MODEL_DIR, PHASE_ID,
                            PHASES, POSITION_ID, POSITIONS, REPORT_DIR, RESULT_ID, RESULTS, TABLE_DIR)
from metafut.models.features import (ACTION_CATEGORICAL, ACTION_PROFILE_START, N_FINE_ZONES, N_ZONES,
                                     PASS_CATEGORICAL, PASS_PROFILE_START, SHOT_CATEGORICAL,
                                     action_matrix, encode_table, fine_zone, pass_matrix, shot_matrix,
                                     zone)
from metafut.models.pools import Pool, rate_table
from metafut.models.profiles import attach, build_profiles, pressing_factor

N_RESULTS, N_PHASES, N_POS, N_HEIGHTS = len(RESULTS), len(PHASES), len(POSITIONS), len(HEIGHT_ID)
N_OCTANTS = 16


def octant(angle):
    return ((np.asarray(angle) + np.pi) / (2 * np.pi) * N_OCTANTS).astype(np.int64) % N_OCTANTS


def ece(y, p, bins=10):
    """Expected calibration error: average gap between predicted and real rates."""
    b = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum(abs(y[b == i].mean() - p[b == i].mean()) * (b == i).mean()
                     for i in range(bins) if (b == i).any()))


def binary_report(y, p):
    return dict(logloss=round(log_loss(y, p), 4), auc=round(roc_auc_score(y, p), 4),
                brier=round(brier_score_loss(y, p), 4), ece=round(ece(y, p), 4))


def valid_passes(d):
    return d[(d.action == "pass") & d.label_valid]


def fit_pass(tr, max_iter=150, X=None):
    tr = valid_passes(tr)
    model = HistGradientBoostingClassifier(max_iter=max_iter, learning_rate=0.1, random_state=0,
                                           categorical_features=PASS_CATEGORICAL)
    return model.fit(pass_matrix(tr) if X is None else X, (tr.result == "pass_complete").astype(int))


def pass_report(model, va, X=None):
    """G0 numbers for the pass model."""
    v = valid_passes(va)
    y = (v.result == "pass_complete").astype(int).values
    p = model.predict_proba(pass_matrix(v) if X is None else X)[:, 1]
    cos = np.cos(v.angle.values)
    gap = lambda m: float(y[m].mean() - p[m].mean())
    rep = binary_report(y, p)
    rep.update(n=int(len(y)), forward_gap=round(gap(cos > 0.7), 4), backward_gap=round(gap(cos < -0.7), 4),
               long_gap=round(gap(v.length.values >= 30), 4), baseline_logloss=round(
                   log_loss(y, np.full(len(y), y.mean())), 4))
    rep["accuracy"] = round(float(((p >= 0.5) == y).mean()), 4)
    return rep


def fit_action(tr, max_iter=80, X=None):
    model = HistGradientBoostingClassifier(max_iter=max_iter, learning_rate=0.12, random_state=0,
                                           max_leaf_nodes=24, categorical_features=ACTION_CATEGORICAL)
    return model.fit(action_matrix(tr) if X is None else X, tr.action.map(ACTION_ID).values)


def action_report(model, tr, va, X=None):
    pv = model.predict_proba(action_matrix(va) if X is None else X)
    yv = va.action.map(ACTION_ID).values
    prior = np.bincount(tr.action.map(ACTION_ID).values, minlength=len(ACTIONS)) / len(tr)
    return dict(
        logloss=round(log_loss(yv, pv, labels=range(len(ACTIONS))), 4),
        baseline_logloss=round(log_loss(yv, np.tile(prior, (len(yv), 1)), labels=range(len(ACTIONS))), 4),
        accuracy=round(float((pv.argmax(1) == yv).mean()), 4))


def blank_profiles(X, start):
    """The same features with every profile column set to zero: a model that ignores profiles."""
    X = X.copy()
    X[:, start:] = 0.0
    return X


def fit_shot(tr):
    s = tr[tr.action == "shot"]
    model = HistGradientBoostingClassifier(max_iter=120, learning_rate=0.06, max_leaf_nodes=12,
                                           min_samples_leaf=40, l2_regularization=1.0, random_state=0,
                                           categorical_features=SHOT_CATEGORICAL)
    return model.fit(shot_matrix(s), (s.result == "shot_goal").astype(int))


def shot_report(model, va):
    s = va[va.action == "shot"]
    y = (s.result == "shot_goal").astype(int).values
    p = model.predict_proba(shot_matrix(s))[:, 1]
    rep = binary_report(y, p)
    valid = s.xg.notna().values
    rep.update(n=int(len(y)), goals=int(y.sum()), predicted_goals=round(float(p.sum()), 1),
               statsbomb_xg_auc=round(roc_auc_score(y[valid], s.xg.values[valid]), 4),
               statsbomb_xg_logloss=round(log_loss(y[valid], s.xg.values[valid]), 4))
    return rep


# Pools are keyed by a 5 by 5 zone, falling back to the 10 by 10 zone and then to a key without
# location when a fine key has too few examples. Near the goal, a few yards change everything.

def transition_keys(result_id, x, y):
    r = np.asarray(result_id, dtype=np.int64)
    return r * N_FINE_ZONES + fine_zone(x, y), [r * N_ZONES + zone(x, y), r]


def pass_shape_keys(phase, x, y, position):
    ph = np.asarray(phase, dtype=np.int64)
    return ((ph * N_FINE_ZONES + fine_zone(x, y)) * N_POS + position,
            [(ph * N_ZONES + zone(x, y)) * N_POS + position, ph])


def pressure_key(prev, x, y, position):
    return (np.asarray(prev, dtype=np.int64) * N_ZONES + zone(x, y)) * N_POS + np.asarray(position, dtype=np.int64)


def carry_keys(x, y, position):
    return (fine_zone(x, y).astype(np.int64) * N_POS + position,
            [zone(x, y).astype(np.int64) * N_POS + position])


def pass_length_keys(phase, x, y, height, oct_, failed):
    """Keys from precise to coarse: 5m zone, then 10m zone, then just height and outcome."""
    def key(z, n_zones):
        k = np.asarray(phase, dtype=np.int64) * n_zones + z
        k = k * N_HEIGHTS + height
        k = k * N_OCTANTS + oct_
        return k * 2 + failed
    return key(fine_zone(x, y), N_FINE_ZONES), [key(zone(x, y), N_ZONES), failed * N_HEIGHTS + height]


def build_pools(tr):
    """Empirical pools and rate tables, learned from the train split."""
    z = zone(tr.x.values, tr.y.values)
    pools = {}

    # Which pass is attempted: height and direction, given where the player is.
    p = tr[tr.action == "pass"]
    fine, (coarse, last) = pass_shape_keys(p.phase_id.values, p.x.values, p.y.values, p.position_id.values)
    pools["pass_shape"] = Pool(
        fine, np.column_stack([p.height_id.values, p.angle.values]), N_PHASES * N_FINE_ZONES * N_POS,
        fallbacks=[(coarse, N_PHASES * N_ZONES * N_POS), (last, N_PHASES)])

    # Where the pass ends and how it fails, given whether it was completed. Drawing the real
    # displacement keeps the end point close to where such passes really land.
    failed = (p.result != "pass_complete").astype(int).values
    fine, (coarse, last) = pass_length_keys(p.phase_id.values, p.x.values, p.y.values,
                                            p.height_id.values, octant(p.angle.values), failed)
    size = N_PHASES * N_HEIGHTS * N_OCTANTS * 2
    pools["pass_length"] = Pool(
        fine, np.column_stack([p.end_x.values - p.x.values, p.end_y.values - p.y.values, p.result_id.values]),
        size * N_FINE_ZONES,
        fallbacks=[(coarse, size * N_ZONES), (last, 2 * N_HEIGHTS)], min_count=8)

    c = tr[tr.action == "carry"]
    fine, (coarse,) = carry_keys(c.x.values, c.y.values, c.position_id.values)
    pools["carry"] = Pool(
        fine, np.column_stack([c.end_x.values - c.x.values, c.end_y.values - c.y.values]),
        N_FINE_ZONES * N_POS, fallbacks=[(coarse, N_ZONES * N_POS)])

    # What happens next: the next decision after each kind of result, keyed by where the ball is.
    linked = tr[tr.has_next == 1]
    ref_x = linked.end_x.fillna(linked.x).values
    ref_y = linked.end_y.fillna(linked.y).values
    same = linked.next_same_team.values
    base_x = np.where(same == 1, ref_x, 120 - ref_x)
    base_y = np.where(same == 1, ref_y, 80 - ref_y)
    next_values = np.column_stack([
        same, linked.next_x.values - base_x, linked.next_y.values - base_y,
        linked.next_x.values, linked.next_y.values,
        linked.next_phase.map(PHASE_ID).values, linked.next_position.map(POSITION_ID).values,
        linked.dt.values, linked.next_same_player.values])
    fine, (coarse, last) = transition_keys(linked.result_id.values, ref_x, ref_y)
    pools["next"] = Pool(fine, next_values, N_RESULTS * N_FINE_ZONES,
                         fallbacks=[(coarse, N_RESULTS * N_ZONES), (last, N_RESULTS)])

    tables = {}
    # Chance of being under pressure in open play, given where the ball is, how it got there and
    # who has it: a goalkeeper holding a caught cross is almost never pressed, a defender next to
    # him usually is. Set pieces are left out: the simulator never applies pressure to them.
    o = tr[tr.phase_id == PHASE_ID["open"]]
    coarse = o.prev_id.values.astype(np.int64) * N_ZONES + zone(o.x.values, o.y.values)
    by_zone = rate_table(coarse, o.pressure.values, N_RESULTS * N_ZONES)
    tables["pressure"] = rate_table(pressure_key(o.prev_id.values, o.x.values, o.y.values, o.position_id.values),
                                    o.pressure.values, N_RESULTS * N_ZONES * N_POS,
                                    base=np.repeat(by_zone, N_POS))
    d = tr[tr.action == "dribble"]
    tables["dribble"] = rate_table(zone(d.x.values, d.y.values) * 2 + d.pressure.values,
                                   (d.result == "dribble_success").astype(int).values, N_ZONES * 2)

    # Length of each half, seconds, including added time.
    ends = tr.groupby(["match_id", "period"]).t.max().unstack()
    tables["half_end"] = np.column_stack([ends[1].values, ends[2].values]).astype(np.float32)

    # Which position takes kick-offs (mostly forwards).
    k = tr[tr.phase_id == PHASE_ID["kick_off"]]
    taker = np.bincount(k.position_id.values, minlength=N_POS).astype(np.float64)
    tables["kickoff_position"] = taker / taker.sum()
    return pools, tables


def real_targets(d):
    """League statistics a simulation has to match, per match."""
    n = d.match_id.nunique()
    passes = d[(d.action == "pass") & d.label_valid]
    return dict(matches=int(n), goals=float((d.result == "shot_goal").sum() / n),
                shots=float((d.action == "shot").sum() / n), passes=float((d.action == "pass").sum() / n),
                completion=float((passes.result == "pass_complete").mean()),
                carries=float((d.action == "carry").sum() / n),
                dribbles=float((d.action == "dribble").sum() / n),
                decisions=float(len(d) / n))


def load_splits():
    d = encode_table(pd.read_parquet(TABLE_DIR / "decisions.parquet"))
    return d[d.split == "train"], d[d.split == "val"]


def train_all(progress=print):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    tr, va = load_splits()
    progress(f"train decisions {len(tr):,}, validation decisions {len(va):,}")
    profiles, tr = build_profiles(tr)
    va = attach(profiles, va)
    progress(f"profiles for {len(profiles.team_names)} teams and {profiles.n_players} players")

    pass_model = fit_pass(tr)
    report = dict(pass_model=pass_report(pass_model, va))
    progress(f"pass {report['pass_model']}")

    # Does the pass model hold up on a league it never saw?
    report["pass_other_league"] = {}
    for league in LEAGUES:
        m = fit_pass(tr[tr.league != league], max_iter=100)
        report["pass_other_league"][league] = pass_report(m, va[va.league == league])["auc"]
    progress(f"leave one league out {report['pass_other_league']}")

    action_model = fit_action(tr)
    report["action_model"] = action_report(action_model, tr, va)
    progress(f"action {report['action_model']}")

    # The same models with the profile columns blanked out show what the profiles add.
    Xp, Xpv = pass_matrix(valid_passes(tr)), pass_matrix(valid_passes(va))
    m = fit_pass(tr, X=blank_profiles(Xp, PASS_PROFILE_START))
    report["pass_model_without_profiles"] = pass_report(m, va, X=blank_profiles(Xpv, PASS_PROFILE_START))
    Xa, Xav = action_matrix(tr), action_matrix(va)
    m = fit_action(tr, X=blank_profiles(Xa, ACTION_PROFILE_START))
    report["action_model_without_profiles"] = action_report(m, tr, va, X=blank_profiles(Xav, ACTION_PROFILE_START))
    del Xp, Xpv, Xa, Xav
    progress(f"without profiles: pass logloss {report['pass_model_without_profiles']['logloss']}, "
             f"action logloss {report['action_model_without_profiles']['logloss']}")

    shot_model = fit_shot(tr)
    report["shot_model"] = shot_report(shot_model, va)
    progress(f"shot {report['shot_model']}")

    pools, tables = build_pools(tr)
    profiles.press_factor = pressing_factor(tr, tables["pressure"], profiles, pressure_key)
    known = pd.concat([tr, va])
    report["targets"] = real_targets(known)
    joblib.dump(dict(pass_model=pass_model, action_model=action_model, shot_model=shot_model,
                     pools=pools, tables=tables, profiles=profiles), MODEL_DIR / BUNDLE)
    (REPORT_DIR / "model_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
