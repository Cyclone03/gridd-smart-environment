import {
  GRIDD_CAPACITY,
  SOUND_COMFORT_FLOOR,
  SOUND_COMFORT_SPAN,
  THERMAL_TARGET_HUMIDITY,
  THERMAL_TARGET_TEMPERATURE,
  THERMAL_WEIGHTS,
} from "../constants/comfort";

const round1 = (value: number) => Math.round(value * 10) / 10;

/**
 * Indice de confort thermique (0–100, indicatif) : pénalise l'écart à la
 * température et à l'humidité de référence (constants/comfort.ts).
 */
export function thermalComfortIndex(temperature: number, humidity: number): number {
  return round1(
    THERMAL_WEIGHTS.temperature * (100 - 10 * Math.abs(temperature - THERMAL_TARGET_TEMPERATURE)) +
      THERMAL_WEIGHTS.humidity * (100 - 2 * Math.abs(humidity - THERMAL_TARGET_HUMIDITY)),
  );
}

/** Indice de confort sonore (≤ 100, indicatif) : décroît au-delà du plancher. */
export function soundComfortIndex(soundLevel: number): number {
  return round1(Math.min(100, 100 - (100 / SOUND_COMFORT_SPAN) * (soundLevel - SOUND_COMFORT_FLOOR)));
}

/** Taux d'occupation (%) par rapport à la capacité de référence. */
export function occupancyRate(occupants: number, capacity = GRIDD_CAPACITY): number {
  return round1((occupants / capacity) * 100);
}
