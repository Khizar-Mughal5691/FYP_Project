# Module 4: React frontend

The complete coded interface required for Phase-I (1 December 2026). It is built in six batches,
and each batch is tested and pushed like a module. This note grows with every batch. The screens
are listed in [../frontend-screens.md](../frontend-screens.md), and the API they call in
[../api.md](../api.md).

| Batch | Screens | Status |
|---|---|---|
| 1. Foundation | Design system, layout, menu, API connection, Home, About | Built 9 November 2026, tested and confirmed by Faizan the same day |
| 2. Teams and players | Teams, team profile, player profile | Next |
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
