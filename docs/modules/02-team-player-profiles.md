# Module 2: Team and player profiles

Status: built 6 November 2026, tested and confirmed by Faizan on 9 November 2026. Gates G0, G1 and
G2 passed, with the same numbers on both machines' runs.

This note feeds the thesis: Chapter 3 (requirements for team and player behaviour), Chapter 4
(design of profiles, fixtures and calibration) and Chapter 5 (implementation and results).

## Why this module exists

In Module 1 both sides of every simulated match were league-average. The proposal promises that
"each player acts as an independent agent with unique attributes and behavioural tendencies".
This module delivers that: every team and every player gets a profile learned from real matches,
and simulated matches use real starting elevens. It also gives the first honest test of whether
the simulator knows anything about real teams: forecasting unseen matches (gate G2).

## What it does

1. **Team profiles.** Seven numbers per team: how well it keeps the ball (pass completion), how
   often it shoots, how often it loses the ball, the same three numbers for opponents playing
   against it, and how often it puts the ball carrier under pressure.
2. **Player profiles.** For every player:
   - the share of each action in their decisions (pass, carry, dribble, shot, loss, clearance)
   - a touch map: where on the pitch they are usually on the ball (24 zones)
   - an involvement weight: decisions per match
   - their own passing and carrying style, drawn from their real examples where there are enough
3. **Partial pooling.** Numbers based on few examples are pulled toward an average. A player with
   little data behaves like a typical player in the same position. A player never seen in
   training (152 of 6,666 validation starters) uses the position average.
4. **Fixtures.** A simulated match takes two real teams and two starting elevens: either the
   elevens that really played or each team's usual eleven (the most frequent starters).
5. **Who has the ball.** After each decision the next player is chosen by position group, by how
   much of the ball they usually see, and by how often they are in that part of the pitch.
6. **Calibration.** One number (the shot scale) is fitted on training fixtures so that the
   composed simulator takes as many shots as real teams did (see below).
7. **Forecast evaluation.** Every validation match is simulated 100 times with its real elevens.
   The forecasts are scored against three baselines.

## Design decisions

| Decision | Reason |
|---|---|
| Profiles are a few interpretable numbers, not team ID columns | They can be explained at a viva and changed by tactics later (Module 3). |
| Leave-one-match-out profiles for training rows | A training row never sees its own match in its profile, so models cannot learn the answer from it. |
| Profiles come from the first 60% of the season only | Validation matches are later in the season, as in real forecasting. |
| Pressure depends on the defending team and on who has the ball | Teams press differently, and goalkeepers are almost never pressed. |
| Receivers are chosen with touch maps | A centre-back and a full-back are both defenders, but only one is usually on the ball in the middle of his own box. |
| One calibration parameter, fitted on training matches | It corrects the sum of small chained biases without touching validation data. |

## Calibration

Each model matches its own training data, but chaining about 1,870 decisions per match let small
biases add up: on training fixtures the simulator took 27.82 shots per match against a real 25.11.
The shot scale multiplies the action model's shot probability and was fitted on 300 training
fixtures × 4 rollouts:

| Step | Shot scale | Simulated shots | Real shots |
|---|---|---|---|
| 0 | 1.0000 | 27.82 | 25.11 |
| 1 | 0.9025 | 26.27 | 25.11 |
| 2 | 0.8626 | 25.75 | 25.11 |
| saved | 0.8412 | not measured on training | 25.11 |

Calibrating a simulator to observed totals is standard practice in agent-based modelling. Here
only training matches are used, so every validation result below remains a fair test.

## Results

### Models (validation matches)

| Model | Without profiles | With profiles |
|---|---|---|
| Pass model log loss | 0.3545 | 0.3539 |
| Pass model AUC | 0.8796 | 0.8801 |
| Action model log loss | 0.4423 | 0.4411 |
| Action model accuracy | 82.13% | 82.34% |

The gain per decision is small. Its value shows at match level, where thousands of decisions add
up. The pass model also holds up on a league left out of training (AUC 0.875 to 0.886).

### Gate G0: pass model

Log loss 0.3539 (limit 0.36), forward and backward gaps −0.0028 and +0.0012 (limit ±0.02),
calibration error 0.0038 (limit 0.01). Passed.

### Gate G1: league-average simulation (1,000 matches)

| Per match | Simulated | Real | Limit | Result |
|---|---|---|---|---|
| Goals | 2.72 | 2.50 | ±10% | Pass |
| Shots | 26.0 | 25.0 | ±10% | Pass |
| Passes | 968 | 974 | ±5% | Pass |
| Pass completion | 76.8% | 77.1% | ±2 points | Pass |
| Time for 1,000 matches | 37.5 to 40.8 s across runs | – | ≤ 120 s | Pass |

### Gate G2: 303 validation matches, 100 rollouts each

Forecasts (lower is better):

| Forecast | RPS | Log score |
|---|---|---|
| Fixed home/draw/away rates | 0.2280 | 1.0795 |
| **Simulator** | **0.2170** | **1.0622** |
| Dixon-Coles | 0.2013 | 1.0061 |
| Bookmaker odds (Pinnacle) | 0.1949 | 0.9754 |

- Simulator minus fixed rates: 95% interval −0.0205 to −0.0006. The simulator is better, and the
  interval excludes zero.
- Simulator minus Dixon-Coles: 95% interval +0.0008 to +0.0303. Dixon-Coles is better.

Team style, simulated against real, correlation across the 80 teams:

| Measure | r |
|---|---|
| Possession (share of passes) | 0.827 |
| Possession, per match | 0.698 |
| Goals scored per match | 0.604 |
| Goals conceded per match | 0.191 |

League statistics on the validation fixtures, with real elevens:

| Per match | Simulated | Real |
|---|---|---|
| Goals | 2.72 | 2.53 |
| Shots | 25.8 | 24.9 |
| Passes | 973 | 977 |
| Pass completion | 76.8% | 76.8% |
| Home win rate | 39.4% | 42.6% |
| Draw rate | 25.3% | 27.1% |

G2 passed: the simulator beats fixed rates, and the possession correlation (0.827) is above the
0.7 limit.

## Problems found and fixed during the build

- **Team names.** In 10 matches the events spell a team differently from the match list
  ("Marseille" against "Olympique de Marseille"). In Module 1 those home teams were treated as
  away teams. Names are now mapped to the match list.
- **The same player keeps the ball after a carry.** In real data 98% of carries are followed by
  the same player's next decision, and 0.9% of passes are. The simulator now follows this.
- **Pool resolution.** Pass direction, carries and "what happens next" were drawn from 10 by 10
  zones, which spread the ball toward the centre near goal. They now use 5 by 5 zones, falling
  back to 10 by 10 where examples are few.
- **Who receives the ball.** Receivers were chosen without regard to location, so full-backs got
  the ball in the middle of their own box. Touch maps fixed this.
- **Pressure.** Pressure ignored who had the ball. Among pressured decisions in a team's own box
  after an intercepted pass, 26% were by the goalkeeper in the simulator, against 1.7% in reality.
  Pressure now depends on position. Clearances after an intercepted pass rose from 44% to 54%
  (real 56%).
- **Goal width.** The shot angle used a 7.32-unit goal; StatsBomb units are yards, so the goal is
  8 units wide.
- **Odds matching.** A name-similarity rule matched one match to the wrong odds row. A team name
  map is now learned from matches that only one odds row fits, and all 1,517 matches match.

The Module 1 idea that low clearances caused the extra shots was tested here. Fixing clearances
did not reduce shots, so that explanation was wrong. The extra shots came from many small chained
biases, which calibration now corrects.

## Limits

- The simulator forecasts better than fixed rates, but worse than Dixon-Coles and the odds. It
  generates whole matches rather than being built only to forecast results.
- Defensive strength is weak: goals conceded correlate only 0.19 with reality. The shot model has
  no defending-team or goalkeeper inputs.
- Home wins are under-simulated (39.4% against 42.6%), and draws slightly too (25.3% against 27.1%).
- Shots are slightly better than real: goals are 7.9% above real on validation fixtures, within
  the gate's 10%.
- Starting elevens play the full match; substitutions are not simulated yet.
- Profiles are fixed after the first 60% of the season and are not updated.

## Files

| File | Responsibility |
|---|---|
| `src/metafut/models/profiles.py` | Team and player profiles, leave-one-match-out values, pressing factors |
| `src/metafut/sim/fixtures.py` | Who plays: real elevens, usual elevens, average teams, team name lookup |
| `src/metafut/sim/calibrate.py` | Fits the shot scale on training fixtures |
| `src/metafut/sim/engine.py` | Simulator: profiles, receiver choice, per-player totals, trace |
| `src/metafut/eval/forecast.py` | RPS and log score, Dixon-Coles, bookmaker odds and their matching |
| `src/metafut/data/actions.py` | Team name mapping, opponent column, same-player link |
| `scripts/05_check_g2.py` | Gate G2 |
| `scripts/simulate_match.py` | Demo: any two teams, event list and 500-rollout summary |
| `tests/test_profiles.py`, `tests/test_forecast.py` | New tests (40 tests in total) |

## Future role

Module 3 adds tactics by changing these profiles: pressing intensity through the pressing factor,
directness through pass style, and formation through the eleven and their positions. The API will
take two team names (and optionally elevens), and the React screens will show the win, draw and
loss probabilities, expected goals and likely scorers that `simulate_match.py` prints today.
