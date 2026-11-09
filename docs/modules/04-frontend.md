# Module 4: React frontend

The complete coded interface required for Phase-I (1 December 2026). It is built in six batches,
and each batch is tested and pushed like a module. This note grows with every batch. The screens
are listed in [../frontend-screens.md](../frontend-screens.md), and the API they call in
[../api.md](../api.md).

| Batch | Screens | Status |
|---|---|---|
| 1. Foundation | Design system, layout, menu, API connection, Home, About | Built 9 November 2026, tested and confirmed by Faizan the same day |
| 2. Teams and players | Teams, team profile, player finder, player profile | Built 9 November 2026, tested and confirmed by Faizan the same day |
| 3. Simulator | Match simulator, results | Planned |
| 4. Interactive | Lineup editor, match replay | Planned |
| 5. Later features (mock data) | Tactics, scenario comparison, outcome analysis, saved scenarios | Planned |
| 6. Polish | Phone and laptop sizes, loading and errors, final screenshots | Planned |

## Why this module exists

Phase-I needs the complete coded interface: every screen of the application, with the two built
features working inside it. Khizar is busy with a job, so the frontend is part of Faizan's work.

## Technology

| Choice | Reason |
|---|---|
| React 19 with Vite 7, in JavaScript | React is named in the proposal; JavaScript matches the proposal and is easier to explain than TypeScript |
| Tailwind CSS 4 | One set of design tokens (colours, fonts) used by every screen |
| React Router 7 | One address per screen, so screens can be bookmarked and linked |
| TanStack Query 5 | API calls with loading, error and retry states handled in one way |
| Motion 12 | Smooth page changes and the animated pitch; switched off for people who ask for reduced motion |
| Recharts 3, lucide-react | Charts (from batch 2) and icons |
| Vitest 3 with Testing Library | Tests that render real pages against a fake API |
| Fonts bundled with the app | The app looks the same without internet, for example at the viva |

Every package version was at least two weeks old when chosen, to avoid brand-new releases.

## Batch 1: Foundation

**Design.** A night pitch: deep green surfaces, chalk-white text, turf green for actions and gold
for highlights. Home and away teams always use the same two colours (mint and amber) on every
screen. Headings use Barlow Condensed (a scoreboard face), body text Manrope, numbers JetBrains
Mono. The background has faint mowing stripes.

**What it does.**
- A menu with all 11 screen groups: a sidebar on laptops, and a drop-down on phones.
- Home: what the project does, live numbers from the API (80 teams, 1,993 players, 4 leagues), an
  animated passing move on a pitch, and the four steps of the method.
- About: the problem, the eight modules and their honest status, the team, the technology, the
  test results (including where the simulator is behind Dixon-Coles and bookmakers), and the
  data credit.
- Screens from later batches already have their place in the menu, with a page that says what
  they will do and in which batch they arrive.
- An API status badge on every page. If the API is not running, the page says so and shows the
  command to start it. While it is offline, the app checks every 10 seconds and recovers on its
  own once the API starts.
- A reusable pitch drawing in StatsBomb units (120 by 80 yards), so later screens can draw API
  coordinates on it directly (heatmaps, lineups, replay).

**Problems found and fixed.**
- Importing `RouterProvider` from `react-router/dom` loaded a second copy of the router in tests,
  and pages could not see it. Everything now imports from `react-router`.
- The test browser cancelled running animations when a test ended and reported 24 errors.
  Animations finish at once in tests now.
- On the home picture, the players and passing line faded in, so a screenshot taken early showed
  an empty pitch. The players are now always visible; only the line and the ball move.
- The headline broke awkwardly ("AT A / TIME"); it now has fixed line breaks.

**Checked.** 10 frontend tests pass: the API client, the home page with live and offline API,
every menu item, a later screen, the About page and the not-found page. The production build
works. Pages were checked in a browser at laptop (1440 px) and phone (375 px) widths.

**Known limit.** The built JavaScript is 507 kB (162 kB compressed). Splitting it per screen is
planned for batch 6.

## Files (batch 1)

| File | Responsibility |
|---|---|
| `frontend/package.json` | Exact package versions and the dev, build and test commands |
| `frontend/vite.config.js` | Build and test settings; port 5173, which the API allows |
| `frontend/src/index.css` | Design tokens: colours, fonts, background |
| `frontend/src/screens.js` | Every screen in one list: menu, routes and "coming soon" pages |
| `frontend/src/routes.jsx`, `src/main.jsx` | Addresses of the pages; app start-up |
| `frontend/src/api/client.js`, `src/api/hooks.js` | Calls to the API and their error messages |
| `frontend/src/components/` | Layout and menu, API badge, pitch drawing, shared UI parts |
| `frontend/src/pages/` | Home, About, coming-soon and not-found pages |
| `frontend/src/test/` | Test set-up and tests |

## Batch 2: Teams and players

The screens of the first Phase-I feature, player behavioural modelling. Everything on them comes
live from the API.

**What it does.**
- **Teams** (`/teams`): all 80 teams in league groups. Filter by league, or search by name; accents
  are ignored, so "atletico" finds Atlético Madrid. The filters are kept in the address, so a
  filtered list can be bookmarked or shared.
- **Team profile** (`/teams/barcelona`): the eight profile numbers as meters that show the team's
  rank among all 80, with its value and the average. A full meter is the best team, whether "best"
  means the highest or the lowest value. Above them, the team's best and lowest ranks. The usual
  eleven stands on a pitch in their usual roles with their shirt numbers, and the squad table sorts
  by any column.
- **Players** (`/players`): a finder for all 1,993 players, most involved first. Search by name and
  filter by league and position; 60 players at a time, up to 200.
- **Player profile** (`/players/5503`): decisions per match against a typical player in the same
  position; the action mix as bars with a tick for the typical player; the clearest differences in
  words ("Dribbles on 5.9% of decisions, 1.6 times as often as a typical forward"); and the touch
  map as a heatmap on a pitch. The touch map switches to the typical player, shows any zone's
  numbers on hover or tap, lists the busiest zones, and has a table view.

**Added to the API (version 1.1).** The screens needed three things the API did not have yet:
- A player finder, `GET /api/players/`. Without it there was no way to find a player by name.
- Short names and shirt numbers. StatsBomb's event files only have full names ("Lionel Andrés Messi
  Cuccittini"). Its lineup files have the names players are known by ("Lionel Messi") and shirt
  numbers. They are now downloaded too (1,517 small files, about 5 minutes) and turned into
  `players.parquet`. Only the interface uses this table; the models never read it.
- Each player's usual role ("Right Wing") and each team's usual formation, taken from the lineups
  table that already existed, so the eleven can be drawn where they really play.

All three are new fields or a new address, so anything written for version 1 keeps working.

**Design decisions.**
- Team badges are shields with the team's letters, coloured from the team's name. The real crests
  belong to the clubs, so they are not used.
- The theme's bright colours are too light for filled chart marks on a dark background. A colour
  checker (lightness, contrast, colour-blind separation) confirmed it, so charts use deeper steps
  of the same hues. The home and away pair for batch 3 passed the same check.
- The touch map uses one colour, brighter for more, and the player and the typical player share
  one scale, so switching between them compares like with like.
- No chart depends on colour or hover alone: values are printed, meters state the rank in words,
  and the touch map has a table view.

**Problems found and fixed.**
- At small sizes, the monospace font's dotted zero looked like an 8 ("20 starts" read as "28").
  Numbers now use the body font with equal-width digits.
- Very small shares showed as "0.0%" (Messi's clearances). They now show as "<0.1%".
- Long full names were cut off in the list under the eleven. The list now uses short names, with
  the role on its own line.
- On a laptop the touch map pitch filled the whole width and was taller than the screen. It now
  sits beside a side panel.
- Searching "suarez" listed Isco before Luis Suárez, because Isco's full name is Francisco Román
  Alarcón Suárez. Players known by the searched name now come first.
- Pages opened by typing their address all shared one scroll-position key, so a new address could
  open part-way down. They are now told apart by their path.

**Checked.**
- 18 frontend tests pass: the 10 from batch 1 and 8 new ones (name and badge helpers, placing the
  eleven, Teams filters, team profile with sorting, an unknown team, player profile with the touch
  map views, and the player finder).
- 63 Python tests pass, including new API tests for the finder (filters, order, bad requests),
  short names and shirt numbers (Lionel Messi, 10), formations, and Suárez before Isco.
- All four screens were checked in a browser at laptop (1440 px) and phone (375 px) widths,
  including hover on the touch map, search, and returning to the same place with Back.

**Known limits.**
- Ranks compare a team with all 80 teams of the four leagues, not only its own league.
- "Shots" is shots as a share of a team's decisions. Barcelona ranks 61st because it makes so many
  passes, not because it shoots rarely. This is worth saying at the viva before someone asks.
- The built JavaScript is now 548 kB (174 kB compressed). Splitting it per screen is planned for
  batch 6.

## Files (batch 2)

| File | Responsibility |
|---|---|
| `frontend/src/pages/Teams.jsx`, `TeamProfile.jsx` | Screens 2 and 3 |
| `frontend/src/pages/Players.jsx`, `PlayerProfile.jsx` | The player finder and screen 4 |
| `frontend/src/components/ProfileMeters.jsx` | The eight team numbers as rank meters |
| `frontend/src/components/LineupPitch.jsx`, `src/lib/lineup.js` | The eleven on a pitch, placed by role |
| `frontend/src/components/ActionMix.jsx`, `TouchMap.jsx` | A player's action mix and touch map |
| `frontend/src/components/TeamBadge.jsx`, `src/lib/teams.js` | Team badges |
| `frontend/src/lib/format.js` | Number and name formats |
| `frontend/src/test/explore.test.jsx`, `fixtures.js` | Batch 2 tests and their sample data |
| `backend/api/services.py`, `views.py`, `urls.py` | Player finder, short names, numbers, roles, formation |
| `src/metafut/data/ingest.py`, `actions.py` | Download lineup files; build `players.parquet` |
