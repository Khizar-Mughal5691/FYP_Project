"""Simulate one league-average match and print what happened. Usage: simulate_match.py [seed]"""
import sys

from metafut.config import ACTIONS, POSITIONS, RESULT_ID
from metafut.sim.engine import Simulator

TEAMS = ("Home", "Away")

if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    r = Simulator().run(1, seed=seed, record_first=True)
    goal = RESULT_ID["shot_goal"]
    for e in r.events:
        if e["result"] == goal:
            minute = int(e["t"] // 60) + 1
            print(f"{minute:>3}'  GOAL {TEAMS[e['team']]} ({POSITIONS[e['position']]}) "
                  f"from x={e['x']:.0f}, y={e['y']:.0f}")
    print(f"\nFinal score: Home {r.goals[0, 0]} - {r.goals[0, 1]} Away")
    for label, row in [("Shots", r.shots[0]), ("xG", r.xg[0].round(2)), ("Passes", r.passes[0]),
                       ("Completed", r.completed[0]), ("Carries", r.carries[0])]:
        print(f"{label:<10} {row[0]:>6}  {row[1]:>6}")
    total = r.ball_seconds[0].sum()
    print(f"{'Possession':<10} {r.ball_seconds[0, 0] / total:>6.0%}  {r.ball_seconds[0, 1] / total:>6.0%}")
    print(f"\n{len(r.events)} decisions simulated, action types: {', '.join(ACTIONS)}")
