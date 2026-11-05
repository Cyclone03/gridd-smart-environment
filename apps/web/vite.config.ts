/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Le frontend est une application autonome : il ne compile plus vers le
// backend Django. En développement, `/api` et `/ws` peuvent être relayés vers
// une API locale ou distante (VITE_DEV_API_PROXY), ce qui évite le CORS.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const apiTarget = env.VITE_DEV_API_PROXY || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    base: "/",
    build: {
      outDir: "dist",
      emptyOutDir: true,
      sourcemap: false,
      rollupOptions: {
        output: {
          manualChunks(id: string) {
            if (id.includes("node_modules/recharts") || id.includes("node_modules/d3-")) return "charts";
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
        "/api": { target: apiTarget, changeOrigin: true },
        "/ws": { target: apiTarget.replace(/^http/, "ws"), ws: true, changeOrigin: true },
      },
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./tests/setup.ts"],
      include: ["tests/**/*.test.{ts,tsx}"],
      restoreMocks: true,
    },
  };
});
