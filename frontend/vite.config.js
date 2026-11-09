import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Port 5173 is the one the Django API allows through CORS.
  server: { port: 5173, strictPort: true },
  test: {
    environment: "happy-dom",
    setupFiles: "./src/test/setup.js",
    css: false,
  },
});
