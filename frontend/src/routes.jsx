import Layout from "./components/Layout";
import About from "./pages/About";
import ComingSoon from "./pages/ComingSoon";
import Home from "./pages/Home";
import NotFound from "./pages/NotFound";
import PlayerProfile from "./pages/PlayerProfile";
import Players from "./pages/Players";
import TeamProfile from "./pages/TeamProfile";
import Teams from "./pages/Teams";
import { BUILT_IN_BATCH, SCREENS } from "./screens";

const comingSoon = SCREENS.filter((s) => s.batch > BUILT_IN_BATCH).map((s) => ({
  path: s.path.slice(1),
  element: <ComingSoon screen={s} />,
}));

export const routes = [
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: "teams", element: <Teams /> },
      { path: "teams/:teamId", element: <TeamProfile /> },
      { path: "players", element: <Players /> },
      { path: "players/:playerId", element: <PlayerProfile /> },
      { path: "about", element: <About /> },
      ...comingSoon,
      { path: "*", element: <NotFound /> },
    ],
  },
];
