import { Droplets, Thermometer, Users, Volume2, Wind, type LucideIcon } from "lucide-react";
import type { DisplayMetric, MetricType } from "../resources/observation";

/** Présentation des mesures dans l'interface (libellés, icônes, couleurs). */
export interface MetricVisual {
  label: string;
  shortLabel: string;
  icon: LucideIcon;
  color: string;
  /** Nombre de décimales affichées. */
  decimals: number;
}

export const METRIC_VISUALS: Record<MetricType, MetricVisual> = {
  temperature: { label: "Température", shortLabel: "Température", icon: Thermometer, color: "#d98519", decimals: 1 },
  humidity: { label: "Humidité", shortLabel: "Humidité", icon: Droplets, color: "#2184a7", decimals: 1 },
  sound_level: { label: "Niveau sonore", shortLabel: "Son", icon: Volume2, color: "#7259bd", decimals: 1 },
  occupancy: { label: "Occupation", shortLabel: "Présence", icon: Users, color: "#c55d45", decimals: 0 },
  co2: { label: "CO₂", shortLabel: "CO₂", icon: Wind, color: "#4c7a3d", decimals: 0 },
};

/** Ordre d'affichage des mesures suivies par l'interface. */
export const DISPLAY_METRICS: DisplayMetric[] = ["temperature", "humidity", "sound_level", "occupancy"];

/** Unités canoniques, utilisées quand une mesure n'a pas encore de valeur. */
export const METRIC_UNITS: Record<MetricType, string> = {
  temperature: "°C",
  humidity: "%",
  sound_level: "dBA",
  occupancy: "personnes",
  co2: "ppm",
};

/** Mesures prises en compte par l'analyse de corrélation. */
export const CORRELATION_METRICS = ["temperature", "humidity", "sound_level"] as const;
export type CorrelationMetric = (typeof CORRELATION_METRICS)[number];

export function isDisplayMetric(value: string | null | undefined): value is DisplayMetric {
  return DISPLAY_METRICS.includes(value as DisplayMetric);
}
