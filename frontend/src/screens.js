// Every screen of the application in one place: the menu, the routes and the "coming soon" pages
// are all built from this list. It follows docs/frontend-screens.md.
import {
  BarChart3, Bookmark, FlaskConical, House, Info, Play, Shield, SlidersHorizontal, Swords, UserRoundSearch, UsersRound,
} from "lucide-react";

export const GROUPS = ["Overview", "Explore", "Simulate", "Plan", "Analyse", "Project"];

export const SCREENS = [
  {
    path: "/", title: "Home", group: "Overview", icon: House, batch: 1,
    module: "Visualization & Interface",
    description: "What Meta-Fut A.I does, with live numbers from the API.",
  },
  {
    path: "/teams", title: "Teams", group: "Explore", icon: Shield, batch: 2,
    module: "Player Dataset Processing",
    description: "All 80 teams of the 2015/16 Premier League, La Liga, Serie A and Ligue 1, each with a profile.",
  },
  {
    path: "/players", title: "Players", group: "Explore", icon: UserRoundSearch, batch: 2,
    module: "Player Behavioural Modelling",
    description: "How each player behaves on the ball: their action mix, involvement and touch map.",
  },
  {
    path: "/simulate", title: "Match simulator", group: "Simulate", icon: Play, batch: 3,
    module: "Event-Driven Simulation Engine",
    description: "Pick two teams, simulate the match hundreds of times, and read the result.",
    features: ["Win, draw and loss chances", "Most likely scorelines", "Likely scorers", "A sample match"],
  },
  {
    path: "/lineups", title: "Lineup editor", group: "Simulate", icon: UsersRound, batch: 4,
    module: "Tactical / Managerial Input",
    description: "Choose the starting eleven on a pitch and simulate with it.",
    features: ["Drag players into positions", "Exactly one goalkeeper", "Simulate with your eleven"],
  },
  {
    path: "/replay", title: "Match replay", group: "Simulate", icon: FlaskConical, batch: 4,
    module: "Visualization & Interface",
    description: "Watch a simulated match play out, decision by decision, on a 2D pitch.",
    features: ["Play, pause and scrub through the match", "Ball path and player names", "Goals and key moments"],
  },
  {
    path: "/tactics", title: "Tactics", group: "Plan", icon: SlidersHorizontal, batch: 5,
    module: "Tactical / Managerial Input",
    description: "Change formation, pressing, tempo and directness before a simulation.",
    features: ["Formation picker", "Pressing, tempo and directness sliders", "Defensive line height"],
  },
  {
    path: "/compare", title: "Scenario comparison", group: "Plan", icon: Swords, batch: 5,
    module: "Scenario Simulation & Rollout",
    description: "Run two versions of the same match side by side and see what changes.",
    features: ["Scenario A against scenario B", "Difference in win chance with an interval"],
  },
  {
    path: "/analysis", title: "Outcome analysis", group: "Analyse", icon: BarChart3, batch: 5,
    module: "Outcome Analysis",
    description: "Shot maps, expected goals over time and player impact from a simulation.",
    features: ["Shot map", "xG timeline", "Player impact table"],
  },
  {
    path: "/saved", title: "Saved scenarios", group: "Analyse", icon: Bookmark, batch: 5,
    module: "Visualization & Interface",
    description: "Simulations you saved, ready to open again.",
    features: ["List of saved simulations", "Open or delete one"],
  },
  {
    path: "/about", title: "About", group: "Project", icon: Info, batch: 1,
    module: "Visualization & Interface",
    description: "The project, the people behind it and the data it uses.",
  },
];

export const BUILT_IN_BATCH = 2;   // screens from later batches show a "coming soon" page for now
