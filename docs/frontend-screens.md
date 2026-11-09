# Screens for the complete coded interface (Phase-I)

Phase-I (1 December 2026) needs the complete coded interface: every screen of the application.
Two features run live through the API; the other screens use mock data until their backend is
built. The API contract is in [api.md](api.md).

Each screen belongs to one of the proposal's eight modules, which helps Chapter 4 and Chapter 5.

| # | Screen | Proposal module | Data | Shows and does |
|---|---|---|---|---|
| 1 | Home | Visualization & Interface | Live: `GET /api/health/` | What Meta-Fut A.I does; quick links; the StatsBomb data credit |
| 2 | Teams | Player Dataset Processing | Live: `GET /api/teams/?league=` | League filter, list of teams; click opens the team profile |
| 3 | Team profile | Player Behavioural Modelling | Live: `GET /api/teams/{team}/` | Eight profile numbers as bars against the league average, with rank out of 80; usual eleven on a pitch; squad table |
| 4 | Player profile | Player Behavioural Modelling | Live: `GET /api/players/` (finder) and `GET /api/players/{id}/` | Find a player by name, league and position; action mix against the position average; decisions per match; touch map as a 6 by 4 heatmap on a pitch |
| 5 | Match simulator | Event-Driven Simulation, Scenario Rollout | Live: `POST /api/simulations/` | Pick home and away teams and the number of rollouts; Run button with a loading state |
| 6 | Simulation results | Outcome Analysis | Live: same response | Win, draw and loss bar; average goals, xG, shots, possession; top scorelines; likely scorers; sample match goals and stats |
| 7 | Lineup editor | Tactical Input | Live: squads from screen 3, sent as `home_xi`/`away_xi` | Choose 11 players and their positions, exactly one GK; simulate with them |
| 8 | Match replay | Visualization | Live: `include_events: true` | 2D pitch; step or play through the sample match's events; ball path, player name, action |
| 9 | Tactics | Tactical / Managerial Input | Mock | Formation picker; sliders for pressing, tempo, directness, defensive line |
| 10 | Scenario comparison | Scenario Simulation & Rollout | Mock | Two scenarios side by side (for example pressing high against low); difference in win chance with an interval |
| 11 | Outcome analysis | Outcome Analysis | Mock | Shot map, xG timeline, player impact table, downloadable summary |
| 12 | Saved scenarios | Visualization | Mock | List of saved simulations; open one again |
| 13 | About | – | Static | Project, group, supervisor, data credit, university |

## Notes

- Screens 2 to 8 work with real data now. Build them first: they are the two Phase-I features,
  and Chapter 5 needs their screenshots.
- Keep mock data in one file, shaped like the real responses in `api.md`, so switching to the
  real API later is a small change.
- Read the API address from one setting (for example `VITE_API_URL=http://127.0.0.1:8000/api`).
- A simulation takes 10 to 20 seconds. Show progress, and do not send the request twice.
- Show every `error` field to the user as it is; the messages are written for people.
- The data credit "Data: StatsBomb open data" must appear in the interface (the About screen
  and the footer are enough).
