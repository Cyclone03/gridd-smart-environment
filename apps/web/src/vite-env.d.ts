/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Adresse de l'API intégrée au bundle (repli si aucune configuration d'exécution). */
  readonly VITE_API_URL?: string;
  /** Adresse WebSocket intégrée au bundle (facultative). */
  readonly VITE_WS_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
