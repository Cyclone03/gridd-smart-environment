import type { MetricType } from "../resources/observation";
import type { Trend } from "../resources/history";

/**
 * Pas d'extrapolation par type de mesure. Heuristique historique de
 * l'interface (dernière moyenne ± un pas selon la tendance), conservée telle
 * quelle : ce n'est pas un modèle de prévision.
 */
const STEP: Partial<Record<MetricType, number>> = {
  temperature: 0.1,
  humidity: 1,
  sound_level: 5,
  occupancy: 1,
};

export function naiveNextValue(lastValue: number | null | undefined, metric: MetricType, trend: Trend | null) {
  if (lastValue == null || trend == null) return null;
  const step = STEP[metric] ?? 0;
  if (trend === "rising") return lastValue + step;
  if (trend === "falling") return lastValue - step;
  return lastValue;
}
