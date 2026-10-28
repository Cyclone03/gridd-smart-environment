/**
 * Accès au stockage local du navigateur, tolérant aux erreurs (navigation
 * privée, stockage bloqué). Réservé aux préférences propres à un navigateur.
 */
export function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeStorage(key: string, value: string | null): void {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    // Stockage indisponible : la préférence n'est simplement pas conservée.
  }
}
