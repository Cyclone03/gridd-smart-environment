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

/** Garde la mesure la plus récente par zone et par type. */
export function latestByZone(observations: Observation[], zones: Zone[]): LatestReadings {
  const zoneCodes = new Map(zones.map((zone) => [zone.id, zone.code]));
  const latest: LatestReadings = new Map();
  for (const observation of observations) {
    const code = observation.zone_code || zoneCodes.get(observation.zone);
    if (!code) continue;
    const key = readingKey(code, observation.type);
    const current = latest.get(key);
    if (!current || Date.parse(observationTime(observation)) > Date.parse(observationTime(current)))
      latest.set(key, { ...observation, zone_code: code });
  }
  return latest;
}

/** Moyenne des dernières valeurs d'un type sur les zones qui le mesurent. */
export function averageLatest(zones: Zone[], latest: LatestReadings, metric: MetricType) {
  const values = zones
    .map((zone) => latest.get(readingKey(zone.code, metric))?.value)
    .filter((value): value is number => value != null);
  return {
    value: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null,
    count: values.length,
    /** Nombre de zones équipées d'un capteur de ce type. */
    expected: zones.filter((zone) => zone.metrics.includes(metric)).length,
  };
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
