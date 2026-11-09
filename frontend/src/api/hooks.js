import { useQuery } from "@tanstack/react-query";
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
