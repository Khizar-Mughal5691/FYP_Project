"""Simulate one match between two real 2015/16 teams, each with its usual starting eleven.

Usage:  simulate_match.py [home team] [away team] [seed]
        simulate_match.py "Barcelona" "Real Madrid" 7
        simulate_match.py --teams        (list every team)
Team names ignore case and accents, so "Atletico Madrid" works.
"""
import sys

import numpy as np

from metafut.config import RESULT_ID
from metafut.sim import fixtures as F
from metafut.sim.engine import Simulator, player_name

ROLLOUTS = 500

if __name__ == "__main__":
    sim = Simulator()
    P = sim.profiles
    if "--teams" in sys.argv:
        print("\n".join(P.team_names))
        sys.exit()
    home = sys.argv[1] if len(sys.argv) > 1 else "Barcelona"
    away = sys.argv[2] if len(sys.argv) > 2 else "Real Madrid"
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    try:
        fx = F.fixture(P, home, away)
    except KeyError as e:
        sys.exit(str(e).strip("'\""))
    home, away = fx.labels[0]

    # One match, told event by event.
    r = sim.run(seed=seed, fixtures=fx, record_first=True)
    names = [[player_name(P, row) for row in fx.players[0, side]] for side in (0, 1)]
    print(f"{home} vs {away}  (usual starting elevens, seed {seed})\n")
    for e in r.events:
        if e["result"] == RESULT_ID["shot_goal"]:
            team = (home, away)[e["team"]]
            print(f"{int(e['t'] // 60) + 1:>3}'  GOAL  {team}: {names[e['team']][e['slot']]}")
    print(f"\nFinal score: {home} {r.goals[0, 0]} - {r.goals[0, 1]} {away}\n")
    total = r.ball_seconds[0].sum()
    print(f"{'':12}{home[:14]:>15}{away[:14]:>15}")
    for label, row in [("Shots", r.shots[0]), ("xG", r.xg[0].round(2)), ("Passes", r.passes[0]),
                       ("Completed", r.completed[0]), ("Possession", (r.ball_seconds[0] / total * 100).round())]:
        print(f"{label:12}{row[0]:>15}{row[1]:>15}")

    # The same fixture many times: what usually happens.
    many = sim.run(seed=seed + 1, fixtures=fx.repeat(ROLLOUTS))
    g = many.goals
    print(f"\nOver {ROLLOUTS} simulations of this fixture:")
    print(f"  {home} win {np.mean(g[:, 0] > g[:, 1]):.0%}   draw {np.mean(g[:, 0] == g[:, 1]):.0%}   "
          f"{away} win {np.mean(g[:, 0] < g[:, 1]):.0%}")
    print(f"  average goals {g[:, 0].mean():.2f} - {g[:, 1].mean():.2f}")
    top = sorted(((many.player_goals[:, side, k].mean(), names[side][k], (home, away)[side])
                  for side in (0, 1) for k in range(11)), reverse=True)[:3]
    print("  most likely scorers: " + ", ".join(f"{n} ({t}) {v:.2f} goals per match" for v, n, t in top))
