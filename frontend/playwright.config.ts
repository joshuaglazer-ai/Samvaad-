import { defineConfig, devices } from "@playwright/test";

// Smoke tests expect the backend on :8000 (LLM_MODE=mock, seeded) and the frontend dev server on :5173.
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  // One retry with a trace, so a flaky test shows up as "flaky" in the report (with a trace to inspect)
  // instead of passing or failing silently.
  retries: 1,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    ...devices["Pixel 5"],
    trace: "on-first-retry",
    // Read-aloud is off in tests so speech synthesis does not block.
  },
  reporter: [["list"]],
});
