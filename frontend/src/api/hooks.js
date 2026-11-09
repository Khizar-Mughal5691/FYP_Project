import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "./client";

// The API's status. While it is offline, check again every 10 seconds, so the app recovers by
// itself once the backend starts.
export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    staleTime: 60_000,
    retry: false,
    refetchInterval: (query) => (query.state.status === "error" ? 10_000 : false),
  });
}

// Profiles do not change while the server runs, so they are fetched once per visit.
const ONCE = { staleTime: Infinity };

export function useTeams() {
  return useQuery({ queryKey: ["teams"], queryFn: () => api.teams(), ...ONCE });
}

export function useTeam(id) {
  return useQuery({ queryKey: ["team", id], queryFn: () => api.team(id), enabled: Boolean(id), ...ONCE });
}

export function usePlayer(id) {
  return useQuery({ queryKey: ["player", id], queryFn: () => api.player(id), enabled: Boolean(id), ...ONCE });
}

// While a new search runs, keep showing the previous results instead of a blank list.
export function usePlayers(params) {
  return useQuery({
    queryKey: ["players", params],
    queryFn: () => api.players(params),
    placeholderData: keepPreviousData,
    ...ONCE,
  });
}
