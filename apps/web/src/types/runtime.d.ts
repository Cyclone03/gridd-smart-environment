/**
 * Configuration d'exécution injectée par `/env.js` (voir server/index.ts).
 * Toutes les valeurs sont publiques.
 */
interface GriddRuntimeConfig {
  API_URL?: string;
  WS_URL?: string;
}

interface Window {
  __GRIDD_CONFIG__?: GriddRuntimeConfig;
}
