import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // jsdom flow tests run in parallel and are CPU-bound; the 5 s default timed out under load on Windows.
    testTimeout: 15_000,
    css: false,
  },
});
