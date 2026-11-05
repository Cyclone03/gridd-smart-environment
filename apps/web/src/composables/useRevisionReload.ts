import { useEffect, useRef } from "react";

/**
 * Recharge une donnée quand `revision` change (événement temps réel), au plus
 * une fois toutes les `minIntervalMs` : une rafale d'événements ne déclenche
 * qu'un seul rechargement.
 */
export function useRevisionReload(revision: number, reload: () => void, minIntervalMs = 15_000) {
  const lastRun = useRef(Date.now());
  const reloadRef = useRef(reload);
  reloadRef.current = reload;

  useEffect(() => {
    if (revision === 0) return;
    const wait = Math.max(0, lastRun.current + minIntervalMs - Date.now());
    const timer = window.setTimeout(() => {
      lastRun.current = Date.now();
      reloadRef.current();
    }, wait);
    return () => window.clearTimeout(timer);
  }, [revision, minIntervalMs]);
}
