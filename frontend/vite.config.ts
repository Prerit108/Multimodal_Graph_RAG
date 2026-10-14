import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const BACKEND = process.env.VITE_API_BASE_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // proxy keeps the browser same-origin in dev, so no CORS surprises
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, "") },
    },
  },
});