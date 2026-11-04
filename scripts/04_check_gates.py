"""Step 4: check gates G0 (pass model) and G1 (simulated league looks like the real one)."""
import json
import time

import pandas as pd

from metafut.config import REPORT_DIR, TABLE_DIR
from metafut.sim.engine import Simulator, summary

ROLLOUTS = 1000


def check(name, value, ok, target):
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<30} {value:<10} target {target}")
    return bool(ok)


def within(sim, real, tol):
    return abs(sim - real) <= tol * real


if __name__ == "__main__":
    report = json.loads((REPORT_DIR / "model_report.json").read_text(encoding="utf-8"))
    pm = report["pass_model"]
    print("G0 pass model (validation matches)")
    g0 = [check("log loss", pm["logloss"], pm["logloss"] <= 0.36, "<= 0.36"),
          check("forward gap", pm["forward_gap"], abs(pm["forward_gap"]) <= 0.02, "within 0.02"),
          check("backward gap", pm["backward_gap"], abs(pm["backward_gap"]) <= 0.02, "within 0.02"),
          check("calibration error", pm["ece"], pm["ece"] <= 0.01, "<= 0.01")]

    real = report["targets"]
    sim = Simulator()
    start = time.perf_counter()
    result = sim.run(ROLLOUTS, seed=1)
    seconds = time.perf_counter() - start
    s = summary(result)

    m = pd.read_parquet(TABLE_DIR / "matches.parquet")
    m = m[m.split != "test"]
    real_home = float((m.home_goals > m.away_goals).mean())
    real_draw = float((m.home_goals == m.away_goals).mean())

    print(f"\nG1 simulated league ({ROLLOUTS} rollouts) against {real['matches']} real matches")
    g1 = [check("goals per match", round(s["goals"], 2), within(s["goals"], real["goals"], 0.10), f"{real['goals']:.2f} +/-10%"),
          check("shots per match", round(s["shots"], 1), within(s["shots"], real["shots"], 0.10), f"{real['shots']:.1f} +/-10%"),
          check("passes per match", round(s["passes"]), within(s["passes"], real["passes"], 0.05), f"{real['passes']:.0f} +/-5%"),
          check("pass completion", round(s["completion"], 3), abs(s["completion"] - real["completion"]) <= 0.02, f"{real['completion']:.3f} +/-0.02"),
          check("seconds for rollouts", round(seconds, 1), seconds <= 120, "<= 120")]
    print("\nFor information")
    print(f"  carries   sim {s['carries']:.0f}  real {real['carries']:.0f}")
    print(f"  dribbles  sim {s['dribbles']:.1f}  real {real['dribbles']:.1f}")
    print(f"  decisions sim {s['decisions']:.0f}  real {real['decisions']:.0f}")
    print(f"  home win  sim {s['home_win']:.3f}  real {real_home:.3f}")
    print(f"  draw      sim {s['draw']:.3f}  real {real_draw:.3f}")

    out = dict(g0=all(g0), g1=all(g1), rollouts=ROLLOUTS, seconds=round(seconds, 1), simulated=s,
               real=real, real_home_win=real_home, real_draw=real_draw)
    (REPORT_DIR / "gates.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nG0 {'PASSED' if out['g0'] else 'FAILED'}, G1 {'PASSED' if out['g1'] else 'FAILED'}")
