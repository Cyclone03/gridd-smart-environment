import { useEffect, useState } from "react";
import { NOW_TICK_MS } from "../constants/app";

/**
 * Heure courante (ms) rafraîchie régulièrement : la fraîcheur des mesures est
 * réévaluée même quand plus aucune donnée n'arrive (cas d'un capteur muet).
 */
export function useNow(intervalMs: number = NOW_TICK_MS): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);
  return now;
}
