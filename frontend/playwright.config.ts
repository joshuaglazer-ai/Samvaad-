import { defineConfig, devices } from "@playwright/test";

// Smoke tests expect the backend on :8000 (LLM_MODE=mock, seeded) and the frontend dev server on :5173.
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    ...devices["Pixel 5"],
    // Read-aloud is off in tests so speech synthesis does not block.
  },
  reporter: [["list"]],
});
