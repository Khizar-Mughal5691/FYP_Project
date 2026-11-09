"""Step 5: gate G2. Simulate every validation match with the real teams and starting elevens and
check two things:
  1. Match forecasts: a lower (better) ranked probability score than fixed home/draw/away rates.
  2. Team style: simulated possession (share of passes) correlates with reality at r >= 0.7.
Dixon-Coles and bookmaker odds are reported as stronger benchmarks. Validation matches only.
"""
import json
import sys
import time

import numpy as np
import pandas as pd

from metafut.config import LEAGUES, REPORT_DIR, TABLE_DIR
from metafut.eval.forecast import (DixonColes, fixed_rates, from_simulation, load_odds, log_score,
                                   match_odds, outcome, paired_interval, rps)
from metafut.models.train import real_targets
from metafut.sim import fixtures as fixture_tools
from metafut.sim.engine import Simulator, summary

ROLLOUTS = int(sys.argv[1]) if len(sys.argv) > 1 else 100


def team_means(frame, value):
    """Average of `value` per team over its matches, home and away rows together."""
    return frame.groupby("team")[value].mean()


if __name__ == "__main__":
    matches = pd.read_parquet(TABLE_DIR / "matches.parquet")
    lineups = pd.read_parquet(TABLE_DIR / "lineups.parquet")
    decisions = pd.read_parquet(TABLE_DIR / "decisions.parquet",
                                columns=["match_id", "team", "action", "result", "label_valid", "split"])
    train = matches[matches.split == "train"]
    val = matches[matches.split == "val"].reset_index(drop=True)
    y = outcome(val.home_goals, val.away_goals)

    sim = Simulator()
    fx = fixture_tools.real_matches(sim.profiles, val.match_id.tolist(), lineups, matches).repeat(ROLLOUTS)
    start = time.perf_counter()
    result = sim.run(seed=7, fixtures=fx)
    seconds = time.perf_counter() - start
    goals = result.goals.reshape(len(val), ROLLOUTS, 2)

    forecasts = {"simulator": from_simulation(goals), "fixed rates": np.tile(fixed_rates(train), (len(val), 1))}
    dc = np.zeros((len(val), 3))
    for league in LEAGUES:
        rows = (val.league == league).to_numpy()
        dc[rows] = DixonColes().fit(train[train.league == league]).predict(val.home[rows], val.away[rows])
    forecasts["Dixon-Coles"] = dc

    odds_note = "not downloaded"
    odds_frames = [match_odds(val[val.league == lg], o) for lg in LEAGUES if (o := load_odds(lg)) is not None]
    if odds_frames:
        odds = pd.concat(odds_frames).set_index("match_id").reindex(val.match_id)
        covered = odds.p_home.notna().to_numpy()
        odds_note = f"{covered.sum()} of {len(val)} matches matched"
        if covered.all():
            forecasts["bookmaker odds"] = odds[["p_home", "p_draw", "p_away"]].to_numpy()

    scores = {name: dict(rps=round(float(rps(p, y).mean()), 4), log_score=round(float(log_score(p, y).mean()), 4),
                         mean_home=round(float(p[:, 0].mean()), 3), mean_draw=round(float(p[:, 1].mean()), 3))
              for name, p in forecasts.items()}
    sim_rps = rps(forecasts["simulator"], y)
    scores["simulator"]["rps_minus_fixed_95ci"] = paired_interval(sim_rps, rps(forecasts["fixed rates"], y))
    scores["simulator"]["rps_minus_dixon_coles_95ci"] = paired_interval(sim_rps, rps(forecasts["Dixon-Coles"], y))

    # Team style: share of the match's passes, simulated against real, averaged per team.
    sim_passes = result.passes.reshape(len(val), ROLLOUTS, 2).mean(axis=1)
    sim_goals = goals.mean(axis=1)
    rows = []
    for k, m in val.iterrows():
        for side, (team, opp) in enumerate([(m.home, m.away), (m.away, m.home)]):
            rows.append(dict(match_id=m.match_id, team=team, sim_share=sim_passes[k, side] / sim_passes[k].sum(),
                             sim_for=sim_goals[k, side], sim_against=sim_goals[k, 1 - side]))
    style = pd.DataFrame(rows)
    real_passes = (decisions[(decisions.split == "val") & (decisions.action == "pass")]
                   .groupby(["match_id", "team"]).size().rename("passes").reset_index())
    real_passes["real_share"] = real_passes.passes / real_passes.groupby("match_id").passes.transform("sum")
    style = style.merge(real_passes[["match_id", "team", "real_share"]], on=["match_id", "team"])
    goals_long = pd.concat([val.assign(team=val.home, real_for=val.home_goals, real_against=val.away_goals),
                            val.assign(team=val.away, real_for=val.away_goals, real_against=val.home_goals)])
    style = style.merge(goals_long[["match_id", "team", "real_for", "real_against"]], on=["match_id", "team"])
    teams = pd.DataFrame({c: team_means(style, c) for c in ["sim_share", "real_share", "sim_for", "real_for",
                                                              "sim_against", "real_against"]})
    corr = lambda a, b: round(float(np.corrcoef(a, b)[0, 1]), 3)
    style_report = dict(teams=len(teams),
                        possession_team_r=corr(teams.sim_share, teams.real_share),
                        possession_match_r=corr(style.sim_share, style.real_share),
                        goals_for_team_r=corr(teams.sim_for, teams.real_for),
                        goals_against_team_r=corr(teams.sim_against, teams.real_against))

    # The same league statistics as gate G1, now on real fixtures.
    real_stats = real_targets(decisions[decisions.match_id.isin(val.match_id)])
    sim_stats = summary(result)
    league = {k: dict(simulated=round(sim_stats[k], 3), real=round(real_stats[k], 3))
              for k in ("goals", "shots", "passes", "completion", "carries", "dribbles", "decisions")}
    league["home_win"] = dict(simulated=round(sim_stats["home_win"], 3), real=round(float((y == 0).mean()), 3))
    league["draw"] = dict(simulated=round(sim_stats["draw"], 3), real=round(float((y == 1).mean()), 3))

    g2_forecast = scores["simulator"]["rps"] < scores["fixed rates"]["rps"]
    g2_style = style_report["possession_team_r"] >= 0.7
    print(f"G2 on {len(val)} validation matches, {ROLLOUTS} rollouts each ({fx.n:,} simulated matches, {seconds:.0f} s)")
    print("\nForecasts (lower is better)")
    for name, s in scores.items():
        print(f"  {name:15s} RPS {s['rps']:.4f}   log score {s['log_score']:.4f}   mean home {s['mean_home']:.3f} draw {s['mean_draw']:.3f}")
    print(f"  simulator minus fixed rates, 95% interval: {scores['simulator']['rps_minus_fixed_95ci']}")
    print(f"  simulator minus Dixon-Coles, 95% interval: {scores['simulator']['rps_minus_dixon_coles_95ci']}")
    print(f"  bookmaker odds: {odds_note}")
    print("\nTeam style, simulated against real (correlation across teams)")
    for k, v in style_report.items():
        print(f"  {k:22s} {v}")
    print("\nLeague statistics on validation fixtures")
    for k, v in league.items():
        print(f"  {k:10s} simulated {v['simulated']:9.3f}   real {v['real']:9.3f}")
    print(f"\n  {'PASS' if g2_forecast else 'FAIL'}  forecast beats fixed rates")
    print(f"  {'PASS' if g2_style else 'FAIL'}  possession correlation across teams >= 0.7")
    out = dict(g2=bool(g2_forecast and g2_style), rollouts=ROLLOUTS, seconds=round(seconds, 1),
               forecasts=scores, odds=odds_note, style=style_report, league=league)
    (REPORT_DIR / "g2.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    teams.round(4).to_csv(REPORT_DIR / "g2_teams.csv")
    print(f"\nG2 {'PASSED' if out['g2'] else 'FAILED'}")
