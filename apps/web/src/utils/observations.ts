import { STALE_READING_MS } from "../constants/app";
import { HIDDEN_ZONE_NAMES } from "../constants/zones";
import type { MetricType, Observation } from "../resources/observation";
import type { Zone } from "../resources/zone";

/** Index des dernières mesures : clé `${codeZone}:${type}`. */
export type LatestReadings = Map<string, Observation>;

export function readingKey(zoneCode: string, metric: MetricType): string {
  return `${zoneCode}:${metric}`;
}

export function observationTime(observation: Observation): string {
  return observation.observed_at || observation.received_at;
}

/** Vrai si la mesure date de moins de `STALE_READING_MS`. */
export function isFresh(observation: Observation | undefined, now: number): observation is Observation {
  return Boolean(observation) && now - Date.parse(observationTime(observation!)) <= STALE_READING_MS;
}

/**
 * Ajoute des mesures à l'index des dernières valeurs en ne gardant que la
 * plus récente par zone et par type. Retourne l'index d'origine (même
 * référence) si rien n'a changé, pour éviter un rendu inutile.
 */
export function mergeLatest(current: LatestReadings, observations: Observation[], zones: Zone[]): LatestReadings {
  const zoneCodes = new Map(zones.map((zone) => [zone.id, zone.code]));
  let next: LatestReadings | null = null;
  for (const observation of observations) {
    const code = observation.zone_code || zoneCodes.get(observation.zone);
    if (!code) continue;
    const key = readingKey(code, observation.type);
    const known = (next ?? current).get(key);
    if (known && Date.parse(observationTime(observation)) <= Date.parse(observationTime(known))) continue;
    next ??= new Map(current);
    next.set(key, { ...observation, zone_code: code });
  }
  return next ?? current;
}

/** Garde la mesure la plus récente par zone et par type. */
export function latestByZone(observations: Observation[], zones: Zone[]): LatestReadings {
  return mergeLatest(new Map(), observations, zones);
}

/**
 * Moyenne des dernières valeurs d'un type sur les zones qui le mesurent.
 * Avec `now`, seules les mesures à jour sont prises en compte : un capteur
 * muet depuis des jours ne fausse pas la moyenne du laboratoire.
 */
export function averageLatest(zones: Zone[], latest: LatestReadings, metric: MetricType, now?: number) {
  const values = zones
    .map((zone) => latest.get(readingKey(zone.code, metric)))
    .filter((item) => (now == null ? item != null : isFresh(item, now)))
    .map((item) => item!.value)
    .filter((value): value is number => value != null);
  return {
    value: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null,
    count: values.length,
    /** Nombre de zones équipées d'un capteur de ce type. */
    expected: zones.filter((zone) => zone.metrics.includes(metric)).length,
  };
}

/** Somme des dernières valeurs (ex. personnes présentes), mêmes règles que ``averageLatest``. */
export function totalLatest(zones: Zone[], latest: LatestReadings, metric: MetricType, now?: number) {
  const average = averageLatest(zones, latest, metric, now);
  return { ...average, value: average.value == null ? null : average.value * average.count };
}

export function visibleZones(zones: Zone[]): Zone[] {
  return zones.filter((zone) => !HIDDEN_ZONE_NAMES.has(zone.name));
}

export function newestTimestamp(observations: Observation[]): Date | null {
  const newest = observations
    .map((item) => Date.parse(observationTime(item)))
    .filter(Number.isFinite)
    .sort((a, b) => b - a)[0];
  return newest ? new Date(newest) : null;
}
