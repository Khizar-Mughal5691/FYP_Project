import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api, ApiError, API_BASE } from "../api/client";
import { SCREENS } from "../screens";
import { fakeApi, HEALTH, offlineApi, renderAt } from "./render";

describe("API client", () => {
  it("calls the API under its base address", async () => {
    const fetch = fakeApi({ "/teams/": [] });
    await api.teams("la_liga");
    expect(fetch.mock.calls[0][0]).toBe(`${API_BASE}/teams/?league=la_liga`);
  });

  it("passes on the API's own error message", async () => {
    fakeApi({});
    await expect(api.team("madrid")).rejects.toMatchObject({ status: 404, message: "not found" });
  });

  it("says how to start the API when it cannot be reached", async () => {
    offlineApi();
    const error = await api.health().catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.offline).toBe(true);
    expect(error.message).toContain("manage.py runserver");
  });

  it("sends simulations as JSON", async () => {
    const fetch = fakeApi({ "/simulations/": { ok: true } });
    await api.simulate({ home: "barcelona", away: "real-madrid" });
    const [, options] = fetch.mock.calls[0];
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ home: "barcelona", away: "real-madrid" });
    expect(options.headers["Content-Type"]).toBe("application/json");
  });
});

describe("Home page", () => {
  it("shows live numbers from the API", async () => {
    fakeApi({ "/health/": HEALTH });
    renderAt("/");
    expect(await screen.findByText("1,993")).toBeInTheDocument();
    expect(screen.getByText("80")).toBeInTheDocument();
    expect(screen.getByText("Serie A")).toBeInTheDocument();
    expect(await screen.findByText("API online")).toBeInTheDocument();
  });

  it("explains how to start the API when it is offline", async () => {
    offlineApi();
    renderAt("/");
    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("Cannot reach the API")).toBeInTheDocument();
    expect(within(alert).getByText("python backend/manage.py runserver")).toBeInTheDocument();
    expect(screen.getByText("API offline")).toBeInTheDocument();
  });
});

describe("Navigation", () => {
  it("lists every screen in the menu", async () => {
    fakeApi({ "/health/": HEALTH });
    renderAt("/");
    const nav = await screen.findAllByRole("navigation", { name: "Main" });
    for (const s of SCREENS) {
      expect(within(nav[0]).getByRole("link", { name: s.title })).toBeInTheDocument();
    }
  });

  it("shows a later screen as coming soon, with its batch", async () => {
    fakeApi({ "/health/": HEALTH });
    renderAt("/tactics");
    expect(await screen.findByRole("heading", { level: 1, name: "Tactics" })).toBeInTheDocument();
    expect(screen.getByText("Arrives in batch 5")).toBeInTheDocument();
  });

  it("shows the About page", async () => {
    fakeApi({ "/health/": HEALTH });
    renderAt("/about");
    expect(await screen.findByRole("heading", { level: 1, name: "Meta-Fut A.I" })).toBeInTheDocument();
    expect(screen.getByText("Sir Ahmad Zia")).toBeInTheDocument();
  });

  it("shows a not-found page for an unknown address", async () => {
    fakeApi({ "/health/": HEALTH });
    renderAt("/no-such-page");
    expect(await screen.findByRole("heading", { name: "Off the pitch" })).toBeInTheDocument();
  });
});

vi.setConfig({ testTimeout: 15000 });
