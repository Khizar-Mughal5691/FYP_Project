# Meta-Fut A.I

A context-aware football match simulator learned from event data. Final Year Project,
Department of Computer Science and IT, The University of Lahore. Supervisor: Sir Ahmad Zia.

The simulator generates a match one on-ball decision at a time: it reads the game state, chooses
an action, resolves the outcome with trained models, and draws what happens next from real
examples of the same situation. Running many matches together gives probabilities for a scenario.

Data: [StatsBomb open data](https://github.com/statsbomb/open-data), 2015/16 Premier League,
La Liga, Serie A and Ligue 1. Data provided by StatsBomb, for non-commercial research use.

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
python scripts/01_download.py       # download about 1,500 matches
python scripts/02_build_tables.py   # build the decisions, matches and lineups tables
python scripts/03_train_models.py   # train models, write reports/model_report.json
python scripts/04_check_gates.py    # check gates G0 and G1
python scripts/simulate_match.py    # simulate one match and print a summary
python -m pytest                    # run the tests
```

## Layout

| Path | What it holds |
|---|---|
| `src/metafut/data` | Download and table building |
| `src/metafut/models` | Features, sampling pools, model training |
| `src/metafut/sim` | The batched match simulator |
| `scripts` | Numbered steps to rebuild everything |
| `reports` | Saved model and gate results |
| `tests` | Automated tests |

## Evaluation rules

Each league is split by date into 60% train, 20% validation and 20% test. Development uses
validation only. The test matches are read once, at the final evaluation.
