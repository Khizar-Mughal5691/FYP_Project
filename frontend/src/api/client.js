// Talks to the Django API. The contract is in docs/api.md.

export const API_BASE = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api").replace(/\/+$/, "");

export const START_API_COMMAND = "python backend/manage.py runserver";

export class ApiError extends Error {
  constructor(message, { status = 0, offline = false } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.offline = offline;
  }
}

async function request(path, { method = "GET", body } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: { Accept: "application/json", ...(body ? { "Content-Type": "application/json" } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(`The API is not running. Start it with: ${START_API_COMMAND}`, { offline: true });
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    // An empty or non-JSON body; the status code still tells what happened.
  }
  if (!response.ok) {
    throw new ApiError(data?.error ?? `The request failed (status ${response.status}).`, { status: response.status });
  }
  return data;
}

// "?search=messi&limit=60" from {search: "messi", limit: 60}, leaving out empty values.
function query(params = {}) {
  const pairs = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return pairs.length ? `?${new URLSearchParams(pairs)}` : "";
}

export const api = {
  health: () => request("/health/"),
  teams: (league) => request(`/teams/${query({ league })}`),
  team: (id) => request(`/teams/${encodeURIComponent(id)}/`),
  players: (params) => request(`/players/${query(params)}`),
  player: (id) => request(`/players/${encodeURIComponent(id)}/`),
  simulate: (body) => request("/simulations/", { method: "POST", body }),
};
