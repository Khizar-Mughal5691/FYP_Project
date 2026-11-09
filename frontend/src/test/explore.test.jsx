// Batch 2: the Teams, team profile, Players and player profile screens, against a fake API.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { api, API_BASE } from "../api/client";
import { pitchName } from "../lib/format";
import { placeEleven } from "../lib/lineup";
import { monogram } from "../lib/teams";
import { BUFFON_ROW, MESSI_ROW, PLAYER, TEAM, TEAMS } from "./fixtures";
import { fakeApi, HEALTH, renderAt } from "./render";

describe("Helpers", () => {
  it("builds player search addresses without empty filters", async () => {
    const fetch = fakeApi({ "/players/": { count: 0, results: [] } });
    await api.players({ search: "messi", league: "", position: undefined, limit: 60 });
    expect(fetch.mock.calls[0][0]).toBe(`${API_BASE}/players/?search=messi&limit=60`);
  });

  it("shortens names for the pitch and teams for their badge", () => {
    expect(pitchName("Lionel Messi")).toBe("Messi");
    expect(pitchName("Kevin De Bruyne")).toBe("De Bruyne");
    expect(pitchName("Neymar")).toBe("Neymar");
    expect(monogram("Real Madrid")).toBe("RM");
    expect(monogram("AS Roma")).toBe("ROM");
    expect(monogram("Olympique de Marseille")).toBe("OM");
  });

  it("places the eleven by role, and spreads players who share one", () => {
    const placed = placeEleven([
      { player_id: 1, position: "GK", role: "Goalkeeper" },
      { player_id: 2, position: "DEF", role: "Right Back" },
      { player_id: 3, position: "FWD", role: "Center Forward" },
      { player_id: 4, position: "FWD", role: "Center Forward" },
      { player_id: 5, position: "MID", role: null },
    ]);
    const at = Object.fromEntries(placed.map((p) => [p.player_id, [p.x, p.y]]));
    expect(at[1][0]).toBeLessThan(at[2][0]);       // the goalkeeper is deepest
    expect(at[2][1]).toBeGreaterThan(60);          // a right back is near y = 80
    expect(at[3][0]).toBe(at[4][0]);
    expect(Math.abs(at[3][1] - at[4][1])).toBeGreaterThanOrEqual(10);
    expect(at[5]).toEqual([52, 40]);               // no role: the middle of its line
  });
});

describe("Teams screen", () => {
  it("lists teams by league and filters them by league and name", async () => {
    fakeApi({ "/health/": HEALTH, "/teams/": TEAMS });
    const user = userEvent.setup();
    renderAt("/teams");
    expect(await screen.findByRole("link", { name: /Barcelona/ })).toHaveAttribute("href", "/teams/barcelona");
    expect(screen.getByRole("heading", { name: /La Liga/ })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Premier League/ }));
    expect(screen.queryByRole("link", { name: /Barcelona/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Arsenal/ })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^All/ }));
    await user.type(screen.getByRole("searchbox", { name: "Search teams" }), "atletico");
    expect(screen.getByRole("link", { name: /Atlético Madrid/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Arsenal/ })).not.toBeInTheDocument();

    await user.clear(screen.getByRole("searchbox", { name: "Search teams" }));
    await user.type(screen.getByRole("searchbox", { name: "Search teams" }), "nowhere");
    expect(screen.getByText('No team matches "nowhere"')).toBeInTheDocument();
  });
});

describe("Team profile", () => {
  it("shows the profile ranks, the usual eleven and the squad", async () => {
    fakeApi({ "/health/": HEALTH, "/teams/barcelona/": TEAM });
    const user = userEvent.setup();
    renderAt("/teams/barcelona");
    expect(await screen.findByRole("heading", { level: 1, name: "Barcelona" })).toBeInTheDocument();
    expect(screen.getByText("Usually 4-3-3")).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Pass completion rank" })).toHaveAttribute("aria-valuetext", "2nd of 80 teams");

    const eleven = screen.getByRole("group", { name: "Barcelona usual eleven" });
    expect(within(eleven).getAllByRole("link")).toHaveLength(11);
    expect(within(eleven).getByRole("link", { name: /Lionel Messi/ })).toHaveAttribute("href", "/players/5503");

    // The squad starts with the most starts; a column header sorts it.
    const squad = screen.getByRole("table");
    const firstPlayer = () => within(within(squad).getAllByRole("row")[1]).getAllByRole("link")[0];
    expect(firstPlayer()).toHaveTextContent("Sergio Busquets");
    await user.click(within(squad).getByRole("button", { name: /Decisions/ }));
    expect(firstPlayer()).toHaveTextContent("Lionel Messi");
    await user.click(within(squad).getByRole("button", { name: /Player/ }));
    expect(firstPlayer()).toHaveTextContent("Andrés Iniesta");
    expect(within(squad).getByText("Substitute only")).toBeInTheDocument();
  });

  it("shows the API's message for an unknown team", async () => {
    fakeApi({ "/health/": HEALTH });
    renderAt("/teams/nowhere");
    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "All teams" })).toHaveAttribute("href", "/teams");
  });
});

describe("Player profile", () => {
  it("shows the action mix, the style in words and the touch map", async () => {
    fakeApi({ "/health/": HEALTH, "/players/5503/": PLAYER });
    const user = userEvent.setup();
    renderAt("/players/5503");
    expect(await screen.findByRole("heading", { level: 1, name: "Lionel Messi" })).toBeInTheDocument();
    expect(screen.getByText("Lionel Andrés Messi Cuccittini")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Barcelona/ })).toHaveAttribute("href", "/teams/barcelona");
    expect(screen.getByText("2.3×")).toBeInTheDocument();

    expect(screen.getByRole("row", { name: /Dribbles 5\.9% 3\.7%/ })).toBeInTheDocument();
    expect(screen.getByText(/Dribbles on 5\.9% of decisions, 1\.6 times as often as a typical forward/)).toBeInTheDocument();
    expect(screen.getByText(/Clears the ball on 0\.4% of decisions, against 2\.1% for a typical forward/)).toBeInTheDocument();

    const map = screen.getByRole("group", { name: "Touch map of Lionel Messi" });
    expect(within(map).getByLabelText("Final third, right centre: 18.0%")).toBeInTheDocument();
    await user.hover(within(map).getByLabelText("Final third, right centre: 18.0%"));
    expect(screen.getByText(/18\.0% for Lionel Messi, 10\.8% for typical forward/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Typical forward" }));
    expect(screen.getByRole("group", { name: "Touch map of a typical forward" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show as a table" }));
    const table = screen.getByRole("table", { name: /a typical forward's decisions in each zone/ });
    expect(within(table).getByRole("columnheader", { name: "Final third" })).toBeInTheDocument();
    expect(within(table).getByRole("row", { name: /Right centre/ })).toHaveTextContent("10.8%");
  });
});

describe("Players screen", () => {
  const players = (url) => {
    const position = url.searchParams.get("position");
    const search = url.searchParams.get("search");
    const results = [MESSI_ROW, BUFFON_ROW].filter((p) =>
      (!position || p.position === position) && (!search || p.name.toLowerCase().includes(search)));
    return { count: results.length, results };
  };

  it("finds players by position and name", async () => {
    const fetch = fakeApi({ "/health/": HEALTH, "/players/": players });
    const user = userEvent.setup();
    renderAt("/players");
    expect(await screen.findByRole("link", { name: /Lionel Messi/ })).toHaveAttribute("href", "/players/5503");
    expect(screen.getByText("2")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Goalkeepers" }));
    await waitFor(() => expect(screen.queryByRole("link", { name: /Lionel Messi/ })).not.toBeInTheDocument());
    expect(screen.getByRole("link", { name: /Gianluigi Buffon/ })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "All" }));
    await user.type(screen.getByRole("searchbox", { name: "Search players" }), "messi");
    await waitFor(() => expect(fetch.mock.calls.some(([u]) => u.includes("search=messi"))).toBe(true));
    await waitFor(() => expect(screen.queryByRole("link", { name: /Gianluigi Buffon/ })).not.toBeInTheDocument());

    await user.type(screen.getByRole("searchbox", { name: "Search players" }), "xyz");
    expect(await screen.findByText('No player matches "messixyz"')).toBeInTheDocument();
  });
});
