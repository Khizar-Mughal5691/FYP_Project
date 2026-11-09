# Meta-Fut A.I

A context-aware football match simulator learned from event data. Final Year Project,
Department of Computer Science and IT, The University of Lahore. Supervisor: Sir Ahmad Zia.

The simulator generates a match one on-ball decision at a time: it reads the game state, lets the
player on the ball choose an action, resolves the outcome with trained models, and draws what
happens next from real examples of the same situation. Every team and player has a profile learned
from real matches, so Barcelona plays differently from Granada, and a winger differently from a
centre-back. Running a fixture many times gives probabilities for its outcome.

Data: [StatsBomb open data](https://github.com/statsbomb/open-data), 2015/16 Premier League,
La Liga, Serie A and Ligue 1. Data provided by StatsBomb, for non-commercial research use.
Bookmaker odds from [football-data.co.uk](https://www.football-data.co.uk) are used only as a
benchmark for match forecasts.

## Setup

Requires Python 3.12. Keep the virtual environment and data outside OneDrive.

```bash
python -m venv ~/.venvs/metafut
~/.venvs/metafut/Scripts/python -m pip install -r requirements.txt
~/.venvs/metafut/Scripts/python -m pip install -e .
```

Data and models are saved in `~/metafut-data`. Set `METAFUT_DATA` to use another folder.

## Build everything

```bash
python scripts/01_download.py       # download about 1,500 matches (events and lineups) and four odds files
python scripts/02_build_tables.py   # build the decisions, matches, lineups and players tables
python scripts/03_train_models.py   # train models and profiles, calibrate, write reports/model_report.json
python scripts/04_check_gates.py    # gates G0 (pass model) and G1 (league-average simulation)
python scripts/05_check_g2.py       # gate G2: forecasts and team style on validation matches
python -m pytest                    # run the tests
```

Data built before 9 November 2026 has no players table, so the interface shows full names without
shirt numbers. To add it without rebuilding everything:

```bash
python scripts/01_download.py       # downloads only the missing lineup files (about 5 minutes)
python -c "from metafut.data.actions import build_players; build_players()"
```

## Try it

```bash
python scripts/simulate_match.py "Barcelona" "Real Madrid"
python scripts/simulate_match.py --teams
```

## Run the API

```bash
python backend/manage.py runserver
```

Then open `http://127.0.0.1:8000/api/teams/` in a browser. The endpoints and their responses are
in [docs/api.md](docs/api.md), and the screens of the interface in
[docs/frontend-screens.md](docs/frontend-screens.md).

## Run the interface

Requires Node.js 22 or newer. Keep the API running in another terminal.

```bash
cd frontend
npm install        # first time only
npm run dev        # then open http://localhost:5173
npm test           # frontend tests
```

## Layout

| Path | What it holds |
|---|---|
| `src/metafut/data` | Download and table building |
| `src/metafut/models` | Features, sampling pools, team and player profiles, model training |
| `src/metafut/sim` | The batched match simulator, fixtures (who plays) and calibration |
| `src/metafut/eval` | Forecast scoring and baselines (Dixon-Coles, bookmaker odds) |
| `backend` | Django REST API: settings, endpoints and the services they call |
| `frontend` | React interface (Vite, Tailwind CSS): pages, components, API client, tests |
| `scripts` | Numbered steps to rebuild everything, plus a match demo |
| `reports` | Saved model and gate results |
| `docs/modules` | One note per module for the thesis |
| `tests` | Automated tests |

## Evaluation rules

Each league is split by date into 60% train, 20% validation and 20% test. Development uses
validation only. The test matches are read once, at the final evaluation.
