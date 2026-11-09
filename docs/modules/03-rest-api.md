# Module 3: REST API for the two Phase-I features

Status: built 9 November 2026, tested and confirmed by Faizan on 9 November 2026.

This note feeds the thesis: Chapter 3 (system environment and interfaces), Chapter 4 (system
architecture) and Chapter 5 (implementation). The full contract for the frontend is in
[../api.md](../api.md), and the list of screens in [../frontend-screens.md](../frontend-screens.md).

## Why this module exists

Phase-I (1 December 2026) needs two major features implemented and the complete coded interface.
Both features already work in Python (Modules 1 and 2), but a React interface cannot call Python
functions directly. The API is the bridge: the interface sends a request over HTTP and receives
JSON. Building it now lets the real screens connect before Phase-I, and gives Chapter 5 real
screenshots.

## What it does

The two features exposed:

1. **Player behavioural modelling:** teams with their eight profile numbers, rank and league
   average; players with their action mix, involvement and touch map.
2. **Event-driven match simulation:** any two of the 80 teams, with their usual elevens or chosen
   elevens, simulated up to 1,000 times. It returns win, draw and loss chances, average statistics,
   frequent scorelines, likely scorers and a sample match that can be replayed event by event.

| Method | Address | Purpose |
|---|---|---|
| GET | `/api/` | Index of every address; the bare site address redirects here |
| GET | `/api/health/` | Status and data credit |
| GET | `/api/teams/` | Team list, optionally by league |
| GET | `/api/teams/{team}/` | Team profile, usual eleven, squad |
| GET | `/api/players/{id}/` | Player profile |
| POST | `/api/simulations/` | Simulate a fixture |

## Design decisions

| Decision | Reason |
|---|---|
| Django 5.2 (long-term support) with Django REST Framework | Named in the proposal; supported until 2028, beyond the FYP |
| The features live in `api/services.py`, with no Django code | They can be tested and reused without a web server; views only translate HTTP |
| No database yet | Profiles and models come from the trained bundle. PostgreSQL arrives with saved scenarios |
| Teams addressed by readable ids (`atletico-madrid`) or by name | Stable addresses for the interface; people can type names without accents |
| One error format, `{"error": "..."}`, with 400 and 404 | The interface can show every error the same way |
| A seed in every simulation | The same request gives the same result, for testing and for the thesis |
| At most 1,000 rollouts | Keeps one request under about a minute on the laptop |
| CORS for the React development server only | The browser blocks other sites from calling the API |

## Faster predictions (models/fast_predict.py)

The first API test showed a fixed cost of about 18 seconds per simulation, whatever the number of
rollouts. Profiling found that 87% of the time went to sklearn's prediction overhead: per-call
input checks and an encoder pipeline (52%), and a Python call for each of about 490 trees per step
(33%). `FastHGB` gives the same predictions with less overhead. It walks all trees together in
numpy for very small batches, calls the compiled trees directly for medium batches, and falls back
to sklearn for large ones.

| Check | Result |
|---|---|
| Largest difference from sklearn's probabilities, 3,000 validation rows per model | 0 to 7×10⁻¹⁶ |
| Simulated matches before and after | identical (same goals and passes) |

| Matches simulated together | Before | After |
|---|---|---|
| 1 | 11.5 s | 2.8 s |
| 50 | 22.7 s | 9.3 s |
| 200 | 29.3 s | 15.0 s |
| 1,000 | 46.5 s | 38.5 s |

## Results

Measured with the development server on the laptop:

| Request | Time |
|---|---|
| Team profile | 0.01 s |
| Simulation, 100 rollouts | 11.8 s |
| Simulation, 200 rollouts (default) | 15.1 s |

- 21 new tests: 6 check that the faster predictions equal sklearn's, for missing values, unknown
  categories and every batch path; 15 check the API, including every error case.
- During Faizan's first test, opening the bare address `http://127.0.0.1:8000/` found no page.
  It now redirects to an index of every address.
- A browser opening a GET address sees a readable page; the React development server is allowed
  through CORS.

## Limits

- A simulation request waits until the simulation ends (10 to 20 seconds). With several users at
  once, a job queue would be needed.
- There are no accounts or logins; the settings are for running on a laptop, not for a public
  server.
- Usual elevens and squads come from the first 60% of the season, like the profiles.
- Tactics, scenario comparison, outcome analysis and saved scenarios have no endpoints yet.

## Files

| File | Responsibility |
|---|---|
| `backend/manage.py` | Django's command tool; starts the server |
| `backend/metafut_api/settings.py` | Settings: apps, CORS, no database, development defaults |
| `backend/metafut_api/urls.py` | Puts the API under `/api/` |
| `backend/api/services.py` | The two features as plain functions: teams, players, simulation |
| `backend/api/views.py` | HTTP endpoints that call the services |
| `backend/api/urls.py` | The five addresses |
| `src/metafut/models/fast_predict.py` | Faster, identical model predictions |
| `tests/test_api.py`, `tests/test_fast_predict.py` | 20 tests |
| `docs/api.md`, `docs/frontend-screens.md` | Contract and screen list for the frontend |

## Future role

The React screens in `docs/frontend-screens.md` are built against this API. After Phase-I the API
grows with the next modules: tactics, scenario comparison, outcome analysis and saved scenarios
(PostgreSQL). For the thesis, the architecture diagram in Chapter 4 is: React interface → REST API
(Django) → services → simulator and models.
