# Module 1: Data pipeline, core models and simulator v0

Status: built 4 November 2026, tested and confirmed by Faizan. Gate G0 passed. Gate G1 passed four
of five checks; goals per match are 10.08% above the real value, against a limit of 10%.

This note feeds the thesis: Chapter 3 (system environment), Chapter 4 (design) and Chapter 5
(implementation and results).

## Why this module exists

Every other module depends on it. Team profiles, tactics, rollouts, the API and the React
screens all call the simulator built here. A football simulator is only credible if its matches
look like real matches, so this module also sets up the measurements (gates) that every later
change is checked against.

## What it does

1. Downloads StatsBomb open data for four full 2015/16 leagues: Premier League, La Liga, Serie A
   and Ligue 1 (1,517 matches).
2. Converts raw events into one table of on-ball decisions (2,846,774 rows). Each row records the
   location, the game state before the decision, and what happened next.
3. Trains three models and builds sampling pools from the training matches:
   - Pass model v2: the probability that a pass succeeds, using its start, direction and height
     plus the game context.
   - Action model: which action the player on the ball chooses (pass, carry, dribble, shot, loss
     of control, clearance).
   - Shot model: the probability that a shot becomes a goal.
   - Sampling pools: real examples drawn when no formula fits, such as where a pass lands or what
     follows a ball going out of play.
4. Simulates full matches one decision at a time. 1,000 matches run together in under a minute.

## Design decisions

| Decision | Reason |
|---|---|
| Simulate on-ball decisions, not 22 moving players | Event data records only the player on the ball, so off-ball movement cannot be learned from it. |
| Leave pass length and end point out of the pass model | StatsBomb records where a failed pass ended, which reveals the outcome (leakage). Direction is known when the ball is kicked, so it stays in. |
| Draw end points and next events from real examples | This keeps set pieces, stoppages and turnovers realistic without a hand-written rule for each. |
| Run all matches together in NumPy arrays | One model call serves every running match. Row-by-row calls would take nearly an hour per 1,000 matches. |
| Split each league by date: 60% train, 20% validation, 20% test | Matches never leak across sets. The test matches stay unread until the final evaluation. |
| Keep data and models outside the repo and outside OneDrive | Data is about 650 MB and is fully rebuilt by the scripts. |

## Files

| File | Responsibility |
|---|---|
| `src/metafut/config.py` | Folder paths, league list, pitch size, split fractions, category names |
| `src/metafut/data/ingest.py` | Downloads match lists and event files, can be restarted |
| `src/metafut/data/actions.py` | Builds the decisions, matches and lineups tables |
| `src/metafut/models/features.py` | Builds model inputs, shared by training and simulation |
| `src/metafut/models/pools.py` | Fast sampling of real examples, smoothed rate tables |
| `src/metafut/models/train.py` | Trains the models, builds the pools, writes `reports/model_report.json` |
| `src/metafut/sim/engine.py` | The batched match simulator |
| `scripts/01_download.py` to `04_check_gates.py` | The numbered steps that rebuild everything |
| `scripts/simulate_match.py` | Simulates one match and prints a summary |
| `tests/` | 17 automated tests |

## Results (validation matches)

| Model | Measure | Result |
|---|---|---|
| Pass v2 | Log loss (baseline 0.542) | 0.3545 |
| Pass v2 | AUC | 0.8796 |
| Pass v2 | Accuracy | 83.7% |
| Pass v2 | Calibration error | 0.0036 |
| Pass v2 | Forward / backward pass gap | −0.0025 / +0.0011 |
| Pass v2 | AUC on a league left out of training | 0.876 to 0.886 |
| Action | Log loss (baseline 1.042) | 0.4423 |
| Action | Accuracy | 82.1% |
| Shot | AUC (StatsBomb's own xG: 0.822) | 0.788 |
| Shot | Goals predicted / real | 775.7 / 765 |

StatsBomb's xG uses information that open event data does not include, so a gap is expected.

## Gate G1: simulated league against real matches

1,000 simulated matches against 1,213 real train and validation matches:

| Per match | Simulated | Real | Limit | Result |
|---|---|---|---|---|
| Goals | 2.76 | 2.50 | ±10% | Fail, 10.08% above real |
| Shots | 26.5 | 25.0 | ±10% | Pass |
| Passes | 983 | 974 | ±5% | Pass |
| Pass completion | 76.9% | 77.1% | ±2 points | Pass |
| Time for 1,000 matches | 48.6 s | – | ≤ 120 s | Pass |

Carries (738 against 733) and dribbles (33.9 against 34.6) also match. The extra goals have two
sources: 6.1% more shots, and slightly better shots (expected goals per shot 0.1035 against 0.1004
real goals per shot). Clearances are lower than real (39.8 against 48.2), which probably lets
attacks continue that would otherwise end. This link has not been tested yet.
Home win and draw rates cannot be compared yet: every simulated team is league-average, while real
leagues mix strong and weak teams.

## Bugs found and fixed during the build

- Matches ended at half-time because the full-time check read the period after it had changed.
- Completed passes and carries could be clipped onto the goal line, creating unrealistic
  close-range shots. They are now redrawn until they land on the pitch.
- Pass length and direction were drawn separately, which spread passes into the six-yard box.
  The simulator now draws a real pass's full displacement.
- The pressure table counted set pieces, where pressure never applies. This made open-play
  pressure too low.

## Limits

- Teams and players are league-average. Module 2 adds team and player profiles.
- Own goals are not simulated (about 0.08 per match in real data).
- 2015/16 data describes historical squads.

## Future role

Module 2 replaces league-average behaviour with team and player profiles. Module 3 adds tactics
on top of the same engine. The API will call `Simulator.run`, and the React screens will show
`SimResult` and the shot log.
