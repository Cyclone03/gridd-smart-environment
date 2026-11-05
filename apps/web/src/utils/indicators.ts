import { GRIDD_CAPACITY, SOUND_COMFORT_FLOOR, SOUND_COMFORT_SPAN } from "../constants/indicators";

const round1 = (value: number) => Math.round(value * 10) / 10;

/** Indice de confort sonore (≤ 100, indicatif) : décroît au-delà du plancher. */
export function soundComfortIndex(soundLevel: number): number {
  return round1(Math.min(100, 100 - (100 / SOUND_COMFORT_SPAN) * (soundLevel - SOUND_COMFORT_FLOOR)));
}

/** Taux d'occupation (%) par rapport à la capacité de référence. */
export function occupancyRate(occupants: number, capacity = GRIDD_CAPACITY): number {
  return round1((occupants / capacity) * 100);
}
