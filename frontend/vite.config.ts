/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
  build: {
    chunkSizeWarningLimit: 900, // three.js chunk is lazy-loaded and never used in Lite mode
    rollupOptions: {
      output: {
        // Keep three.js out of the initial bundle (it is lazy-loaded with the 3D scenes).
        manualChunks(id: string) {
          // React must have its own chunk, otherwise it is pulled into "three" and that chunk loads eagerly.
          if (/node_modules[\\/](react|react-dom|scheduler|react-router|react-router-dom|@remix-run)[\\/]/.test(id)) return "vendor";
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
