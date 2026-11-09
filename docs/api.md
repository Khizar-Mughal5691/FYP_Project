# Meta-Fut A.I REST API

The contract between the Django backend and the React frontend. Version 1, 9 November 2026.
Every response is JSON. Field names use snake_case.

## Running it

```bash
python backend/manage.py runserver
```

The API is then at `http://127.0.0.1:8000/api/`. Opening any GET address in a browser shows a
readable page with the JSON. The React development server on port 5173 (Vite) or 3000 is allowed
to call the API (CORS). The first request after starting the server loads the models and takes a
few seconds longer.

## Endpoints

| Method | Address | What it returns | Feature |
|---|---|---|---|
| GET | `/api/` | Every address below, as links (the bare `http://127.0.0.1:8000/` opens this) | – |
| GET | `/api/health/` | Status, model, number of teams and players, leagues, data credit | – |
| GET | `/api/teams/` | All 80 teams; `?league=la_liga` gives one league | Profiles |
| GET | `/api/teams/{team}/` | One team's profile numbers, usual eleven and squad | Profiles |
| GET | `/api/players/{player_id}/` | One player's action mix, involvement and touch map | Profiles |
| POST | `/api/simulations/` | Simulate a fixture many times: chances, scorelines, likely scorers, a sample match | Simulation |

`{team}` is a team id such as `barcelona` or `atletico-madrid`. A plain name such as
`Atletico Madrid` also works; case and accents are ignored.

League ids: `premier_league`, `la_liga`, `serie_a`, `ligue_1`.

Positions: `GK`, `DEF`, `MID`, `FWD`.

## Errors

Every error has the same shape:

```json
{"error": "unknown team 'madrid'. Did you mean one of: Atlético Madrid, Real Madrid"}
```

| Status | When |
|---|---|
| 400 | The request is wrong: a missing field, the same team twice, 0 rollouts, an eleven without 11 players |
| 404 | The team or player does not exist |
| 405 | The wrong method, for example GET on `/api/simulations/` |

Show the `error` text to the user. It is written to be read by a person.

## GET /api/teams/{team}/

```json
{
  "id": "barcelona", "name": "Barcelona", "league": "la_liga", "league_name": "La Liga",
  "profile": [
    {"key": "att_pass", "label": "Pass completion", "value": 0.8547, "league_average": 0.7726,
     "better": "higher", "rank": 2, "out_of": 80}
  ],
  "usual_xi": [{"player_id": 4691, "name": "Claudio Andrés Bravo Muñoz", "position": "GK"}],
  "squad": [{"player_id": 5246, "name": "Luis Alberto Suárez Díaz", "position": "FWD",
             "starts": 21, "matches": 21, "decisions": 1455}],
  "credit": "Data: StatsBomb open data, 2015/16 season, used for non-commercial research."
}
```

- `profile` always has eight numbers, in the order `att_pass`, `att_shot`, `att_loss`, `def_pass`,
  `def_shot`, `def_loss`, `def_press`, `press_factor`.
- `rank` is 1 for the best of the 80 teams. `better` says whether a higher or a lower value is
  better, so a bar chart can colour it.
- `usual_xi` always has 11 players with exactly one `GK`.
- `squad` is everyone who played for the team in the training matches, most starts first.

## GET /api/players/{player_id}/

```json
{
  "player_id": 5503, "name": "Lionel Andrés Messi Cuccittini", "position": "FWD",
  "teams": [{"id": "barcelona", "name": "Barcelona", "league": "la_liga", "league_name": "La Liga",
             "starts": 15, "matches": 17, "decisions": 2186}],
  "actions": [{"action": "dribble", "share": 0.0589, "position_average": 0.037}],
  "involvement": {"decisions_per_match": 116.81, "position_average": 50.05},
  "touch_map": {"columns": 6, "rows": 4, "zone_size_yards": [20, 20],
                "values": [0.0002, 0.0007, "... 24 values ..."],
                "position_average": ["... 24 values ..."]}
}
```

- `actions` always lists `pass`, `carry`, `dribble`, `shot`, `loss` and `clear`, and the shares
  add up to 1. `position_average` is the typical player in the same position, for comparison.
- `touch_map.values[column + 6 * row]` is the share of the player's decisions in that 20 by 20
  yard zone. Column 0 is next to the player's own goal and column 5 next to the opponent's; row 0
  is one touchline (y 0 to 20). Draw it as a 6 by 4 heatmap on a pitch.

## POST /api/simulations/

Request:

```json
{"home": "barcelona", "away": "real-madrid", "rollouts": 200, "seed": 7, "include_events": false}
```

| Field | Required | Meaning |
|---|---|---|
| `home`, `away` | yes | Team id or name; must be different teams |
| `rollouts` | no, default 200 | How many times to simulate the match, 1 to 1000 |
| `seed` | no, random | The same seed gives exactly the same result |
| `home_xi`, `away_xi` | no, usual eleven | 11 items of `{"player_id": 5503, "position": "FWD"}`, exactly one GK, no player twice |
| `include_events` | no, default false | Add every decision of the sample match (about 1,900 rows) for a pitch replay |

Response (shortened):

```json
{
  "home": {"id": "barcelona", "name": "Barcelona", "league": "la_liga", "league_name": "La Liga"},
  "away": {"id": "real-madrid", "name": "Real Madrid", "league": "la_liga", "league_name": "La Liga"},
  "rollouts": 100, "seed": 7,
  "probabilities": {"home_win": 0.49, "draw": 0.29, "away_win": 0.22},
  "average": {"home": {"goals": 2.16, "xg": 1.835, "shots": 14.86, "passes": 538.0,
                       "pass_completion": 0.831, "possession": 0.522},
              "away": {"...": "same fields"}},
  "scorelines": [{"home": 2, "away": 2, "probability": 0.14}],
  "likely_scorers": [{"team": "home", "player_id": 5246, "name": "Luis Alberto Suárez Díaz",
                      "position": "FWD", "slot": 1, "goals_per_match": 0.45, "shots_per_match": 2.78}],
  "lineups": {"home": [{"player_id": 4691, "name": "Claudio Andrés Bravo Muñoz", "position": "GK", "slot": 0}],
              "away": ["... 11 players ..."]},
  "sample_match": {
    "score": {"home": 0, "away": 1},
    "goals": [{"minute": 68, "team": "away", "player_id": 5552, "player": "Marcelo Vieira da Silva Júnior"}],
    "stats": {"home": {"shots": 9, "xg": 0.67, "passes": 539, "completed": 426, "possession": 0.528},
              "away": {"...": "same fields"}},
    "events": [{"minute": 1, "second": 0, "team": "home", "player_id": 5246, "player": "...",
                "position": "FWD", "action": "pass", "result": "pass_complete",
                "x": 60.0, "y": 40.0, "end_x": 55.1, "end_y": 38.2, "under_pressure": false}]
  },
  "seconds": 11.2, "model": "simulator_v1.joblib", "credit": "..."
}
```

- `probabilities` add up to 1. `scorelines` lists the 10 most frequent results.
- `average.*.goals` is the mean of the simulated scores; `xg` is expected goals.
- `sample_match` is the first of the simulated matches. `events` is only there when
  `include_events` is true. Coordinates are StatsBomb yards: x 0 to 120 from the acting team's
  own goal to the opponent's goal, y 0 to 80.
- Action names: `pass`, `carry`, `dribble`, `shot`, `loss`, `clear`. Result names add the
  outcome, for example `pass_complete`, `pass_incomplete`, `shot_goal`, `dribble_success`.

**Timing.** On the development laptop, 100 rollouts take about 12 seconds and 200 about
15 seconds. Show a loading state, and keep the button disabled while a simulation runs.

## Not built yet

These screens are part of the complete interface, but their endpoints come after Phase-I. Build
them with mock data in the shapes above:

- tactics (formation, pressing, tempo, directness)
- scenario comparison (A against B)
- outcome analysis (shot maps, player impact)
- saved scenarios

See [frontend-screens.md](frontend-screens.md).
