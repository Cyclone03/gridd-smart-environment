/**
 * Point d'entrée du serveur de production : `node dist-server/index.js`.
 *
 * Variables : PORT (3000), HOST (0.0.0.0), STATIC_DIR (../dist),
 * GRIDD_API_URL, GRIDD_WS_URL, LOG_REQUESTS (false).
 */
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildRuntimeConfig, createGriddServer } from "./app.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT ?? 3000);
const host = process.env.HOST ?? "0.0.0.0";
const staticDir = path.resolve(process.env.STATIC_DIR ?? path.join(here, "..", "dist"));

const server = createGriddServer({
  staticDir,
  logRequests: process.env.LOG_REQUESTS === "true",
});

server.listen(port, host, () => {
  const config = buildRuntimeConfig(process.env);
  console.log(`[web] GRIDD frontend sur http://${host}:${port} (fichiers : ${staticDir})`);
  console.log(`[web] API : ${config.API_URL ?? "(même origine)"} · WebSocket : ${config.WS_URL ?? "(déduit)"}`);
});

server.on("error", (error) => {
  console.error("[web] Erreur fatale :", error);
  process.exit(1);
});

for (const signal of ["SIGTERM", "SIGINT"] as const) {
  process.on(signal, () => {
    console.log(`[web] ${signal} reçu, arrêt…`);
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 5000).unref();
  });
}
