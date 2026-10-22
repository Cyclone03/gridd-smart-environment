import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const rootDirectory = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [react()],
  base: "/static/dashboard/",
  build: {
    outDir: resolve(rootDirectory, "../gridd_django/static/dashboard"),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "dashboard.js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: "dashboard.[ext]",
        manualChunks(id) {
          if (id.includes("node_modules/recharts")) return "charts";
          if (id.includes("node_modules/lucide-react")) return "icons";
          if (id.includes("node_modules/react")) return "react";
          return undefined;
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/ws": {
        target: "ws://127.0.0.1:8000",
        ws: true,
      },
    },
  },
});
