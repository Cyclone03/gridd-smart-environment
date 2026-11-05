/**
 * Serveur HTTP de production du frontend GRIDD (Node.js, sans dépendance).
 *
 * Rôle :
 * - servir les fichiers compilés par Vite (dossier `dist/`) ;
 * - renvoyer `index.html` pour les routes de l'application (navigation SPA) ;
 * - générer `/env.js` à partir des variables d'environnement publiques, ce
 *   qui permet de changer l'adresse de l'API sans recompiler l'image ;
 * - exposer `/healthz` pour les contrôles de santé Docker.
 *
 * Seules les variables listées dans PUBLIC_ENV sont transmises au navigateur.
 */
import { createReadStream } from "node:fs";
import { readFile, stat } from "node:fs/promises";
import http from "node:http";
import path from "node:path";

/** Variables d'environnement → clés exposées dans window.__GRIDD_CONFIG__. */
const PUBLIC_ENV: Record<string, string> = {
  GRIDD_API_URL: "API_URL",
  GRIDD_WS_URL: "WS_URL",
};

const MIME_TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".map": "application/json",
  ".txt": "text/plain; charset=utf-8",
  ".webmanifest": "application/manifest+json",
};

const SECURITY_HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "X-Frame-Options": "DENY",
};

export interface ServerOptions {
  /** Dossier contenant le build Vite (index.html, assets/). */
  staticDir: string;
  /** Variables d'environnement (process.env par défaut). */
  env?: NodeJS.ProcessEnv;
  logRequests?: boolean;
}

export function buildRuntimeConfig(env: NodeJS.ProcessEnv): Record<string, string> {
  const config: Record<string, string> = {};
  for (const [variable, key] of Object.entries(PUBLIC_ENV)) {
    const value = env[variable]?.trim();
    if (value) config[key] = value;
  }
  return config;
}

export function renderEnvScript(config: Record<string, string>): string {
  // JSON échappé pour empêcher toute fermeture de balise script.
  const json = JSON.stringify(config).replace(/</g, "\\u003c");
  return `// Généré au démarrage du serveur — valeurs publiques uniquement.\nwindow.__GRIDD_CONFIG__ = ${json};\n`;
}

async function fileExists(filePath: string): Promise<boolean> {
  try {
    return (await stat(filePath)).isFile();
  } catch {
    return false;
  }
}

export function createGriddServer({ staticDir, env = process.env, logRequests = false }: ServerOptions) {
  const root = path.resolve(staticDir);
  const indexPath = path.join(root, "index.html");
  const envScript = renderEnvScript(buildRuntimeConfig(env));

  const send = (
    res: http.ServerResponse,
    status: number,
    body: string,
    headers: Record<string, string> = {},
    headOnly = false,
  ) => {
    res.writeHead(status, {
      ...SECURITY_HEADERS,
      "Content-Type": "text/plain; charset=utf-8",
      "Content-Length": Buffer.byteLength(body),
      ...headers,
    });
    res.end(headOnly ? undefined : body);
  };

  return http.createServer(async (req, res) => {
    const started = Date.now();
    if (logRequests)
      res.on("finish", () => console.log(`[web] ${req.method} ${req.url} ${res.statusCode} ${Date.now() - started}ms`));

    if (req.method !== "GET" && req.method !== "HEAD") {
      send(res, 405, "Méthode non autorisée", { Allow: "GET, HEAD" });
      return;
    }
    const headOnly = req.method === "HEAD";

    let pathname: string;
    try {
      pathname = decodeURIComponent(new URL(req.url ?? "/", "http://localhost").pathname);
    } catch {
      send(res, 400, "Requête invalide", {}, headOnly);
      return;
    }

    if (pathname === "/healthz") {
      send(
        res,
        200,
        JSON.stringify({ status: "ok" }),
        { "Content-Type": "application/json", "Cache-Control": "no-store" },
        headOnly,
      );
      return;
    }
    if (pathname === "/env.js") {
      send(
        res,
        200,
        envScript,
        { "Content-Type": "text/javascript; charset=utf-8", "Cache-Control": "no-store" },
        headOnly,
      );
      return;
    }

    const filePath = path.join(root, path.normalize(pathname));
    if (filePath !== root && !filePath.startsWith(root + path.sep)) {
      send(res, 403, "Accès refusé", {}, headOnly);
      return;
    }

    const extension = path.extname(filePath).toLowerCase();
    let target = filePath;
    if (!(await fileExists(filePath))) {
      // Un fichier manquant avec extension (ex. ancien bundle) → 404 ;
      // une route applicative sans extension → index.html.
      if (extension) {
        send(res, 404, "Fichier introuvable", {}, headOnly);
        return;
      }
      target = indexPath;
    }

    try {
      const isIndex = target === indexPath;
      const isHashedAsset = target.startsWith(path.join(root, "assets") + path.sep);
      const headers = {
        ...SECURITY_HEADERS,
        "Content-Type": MIME_TYPES[path.extname(target).toLowerCase()] ?? "application/octet-stream",
        "Cache-Control": isHashedAsset ? "public, max-age=31536000, immutable" : "no-cache",
      };
      if (isIndex) {
        const body = await readFile(target);
        res.writeHead(200, { ...headers, "Content-Length": body.byteLength });
        res.end(headOnly ? undefined : body);
        return;
      }
      const { size } = await stat(target);
      res.writeHead(200, { ...headers, "Content-Length": size });
      if (headOnly) res.end();
      else createReadStream(target).pipe(res);
    } catch (error) {
      console.error(`[web] Erreur lors de l'envoi de ${target}:`, error);
      if (!res.headersSent) send(res, 500, "Erreur interne", {}, headOnly);
      else res.destroy();
    }
  });
}
