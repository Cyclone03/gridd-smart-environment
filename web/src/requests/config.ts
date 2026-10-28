/**
 * Adresses de l'API et du WebSocket.
 *
 * Ordre de priorité :
 * 1. configuration d'exécution `window.__GRIDD_CONFIG__` (fichier /env.js
 *    généré par le serveur Node à partir de GRIDD_API_URL / GRIDD_WS_URL) ;
 * 2. variables de compilation Vite `VITE_API_URL` / `VITE_WS_URL` ;
 * 3. même origine que la page (développement avec le proxy Vite, ou
 *    reverse proxy qui relaie /api et /ws).
 *
 * Ces valeurs sont publiques : aucun secret ne doit transiter par ici.
 */

function clean(value: string | undefined | null): string {
  return (value ?? "").trim().replace(/\/+$/, "");
}

export function getApiBaseUrl(): string {
  const runtime = typeof window !== "undefined" ? window.__GRIDD_CONFIG__?.API_URL : undefined;
  return clean(runtime) || clean(import.meta.env.VITE_API_URL);
}

export function getWsBaseUrl(): string {
  const runtime = typeof window !== "undefined" ? window.__GRIDD_CONFIG__?.WS_URL : undefined;
  const explicit = clean(runtime) || clean(import.meta.env.VITE_WS_URL);
  if (explicit) return explicit;

  const api = getApiBaseUrl();
  if (api) return api.replace(/^http(s?):/i, (_match, secure: string) => `ws${secure}:`);

  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.host}`;
}

export function buildApiUrl(path: string): string {
  return `${getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
}

export function buildWsUrl(path: string): string {
  return `${getWsBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
}
