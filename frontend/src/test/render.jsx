// Render the real app routes at an address, with a fresh data cache and a fake API.
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router";
import { vi } from "vitest";
import { routes } from "../routes";

export function renderAt(path) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

// fetch answers from a table of path -> JSON body, or path -> function of the URL that returns the
// body (to answer by query string); anything else is a 404.
export function fakeApi(responses) {
  const fetch = vi.fn(async (url) => {
    const address = new URL(url);
    const entry = responses[address.pathname.replace(/^\/api/, "")];
    const body = typeof entry === "function" ? entry(address) : entry;
    return new Response(JSON.stringify(body ?? { error: "not found" }), { status: body ? 200 : 404 });
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

export function offlineApi() {
  vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
}

export const HEALTH = {
  status: "ok", model: "simulator_v1.joblib", teams: 80, players: 1993,
  leagues: [
    { id: "premier_league", name: "Premier League" }, { id: "la_liga", name: "La Liga" },
    { id: "serie_a", name: "Serie A" }, { id: "ligue_1", name: "Ligue 1" },
  ],
  credit: "Data: StatsBomb open data, 2015/16 season, used for non-commercial research.",
};
