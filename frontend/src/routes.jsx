import Layout from "./components/Layout";
import About from "./pages/About";
import ComingSoon from "./pages/ComingSoon";
import Home from "./pages/Home";
import NotFound from "./pages/NotFound";
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
      { path: "about", element: <About /> },
      ...comingSoon,
      { path: "*", element: <NotFound /> },
    ],
  },
];
