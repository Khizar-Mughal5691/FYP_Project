import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// Both come from "react-router" itself. Importing RouterProvider from "react-router/dom" can load
// a second copy of the router in tests, and then pages cannot see the router.
import { createBrowserRouter, RouterProvider } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { routes } from "./routes";
import "./index.css";

// Try a failed request once more, unless the API answered that the request itself is wrong
// (for example an unknown team): asking again would get the same answer.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failures, error) => failures < 1 && !(error?.status >= 400 && error?.status < 500),
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={createBrowserRouter(routes)} />
    </QueryClientProvider>
  </StrictMode>,
);
