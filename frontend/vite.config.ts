/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
  build: {
    rollupOptions: {
      output: {
        // Keep three.js out of the initial bundle (it is lazy-loaded with the 3D scenes).
        manualChunks(id: string) {
          if (/node_modules[\\/](three|@react-three|three-stdlib|maath|troika)/.test(id)) return "three";
          if (/node_modules[\\/](recharts|d3-|victory-vendor)/.test(id)) return "charts";
          if (/node_modules[\\/](leaflet|react-leaflet|@react-leaflet)/.test(id)) return "map";
          return undefined;
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
