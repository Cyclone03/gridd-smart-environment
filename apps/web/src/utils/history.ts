/**
 * Mise à jour en direct d'un historique agrégé (GET /api/zones/<code>/history/)
 * avec les mesures reçues par le WebSocket.
 *
 * Les créneaux et les statistiques sont calculés exactement comme côté API
 * (modules/history) : créneaux alignés sur l'heure locale du serveur,
 * moyenne / minimum / maximum / nombre par créneau, tendance comparant le
 * premier et le dernier créneau à une tolérance propre à la mesure.
 */
import type { HistoryPoint, Trend, ZoneHistory } from "../resources/history";
import type { Observation } from "../resources/observation";
import { observationTime } from "./observations";

const MINUTE_MS = 60_000;

/** Décalage UTC (minutes) d'une date ISO 8601 : `-05:00` → -300, `Z` → 0. */
export function utcOffsetMinutes(iso: string): number {
  const match = /([+-])(\d{2}):?(\d{2})$/.exec(iso);
  if (!match) return 0;
  const minutes = Number(match[2]) * 60 + Number(match[3]);
  return match[1] === "-" ? -minutes : minutes;
}

/** Début (ms) du créneau contenant `time`, aligné sur l'heure locale du serveur. */
export function bucketStartMs(time: number, bucketMinutes: number, offsetMinutes: number): number {
  const bucketMs = bucketMinutes * MINUTE_MS;
  const offsetMs = offsetMinutes * MINUTE_MS;
  return Math.floor((time + offsetMs) / bucketMs) * bucketMs - offsetMs;
}

function trendOf(points: HistoryPoint[], tolerance: number): Trend {
  if (points.length < 2) return "stable";
  const delta = points[points.length - 1].average - points[0].average;
  if (delta > tolerance) return "rising";
  if (delta < -tolerance) return "falling";
  return "stable";
}

const round2 = (value: number) => Math.round(value * 100) / 100;

/** Statistiques de la période à partir des créneaux (identiques au calcul de l'API). */
export function summarizePoints(points: HistoryPoint[], tolerance: number): ZoneHistory["statistics"] {
  const count = points.reduce((sum, point) => sum + point.count, 0);
  if (!count) return { minimum: null, maximum: null, average: null, count: 0, trend: "stable" };
  return {
    minimum: Math.min(...points.map((point) => point.minimum)),
    maximum: Math.max(...points.map((point) => point.maximum)),
    average: round2(points.reduce((sum, point) => sum + point.average * point.count, 0) / count),
    count,
    trend: trendOf(points, tolerance),
  };
}

/**
 * Ajoute à l'historique les mesures de sa zone et de sa mesure.
 *
 * Seules les mesures postérieures à la fin de la requête (`history.end`) sont
 * ajoutées : les précédentes sont déjà comptées par l'API. `until` borne les
 * périodes fixes. Retourne le même objet si rien n'a changé.
 */
export function mergeObservations(
  history: ZoneHistory,
  observations: Observation[],
  tolerance: number,
  until: number = Number.POSITIVE_INFINITY,
): ZoneHistory {
  const from = Date.parse(history.end);
  const offset = utcOffsetMinutes(history.start);
  const bucketMs = history.bucket_minutes * MINUTE_MS;
  let points: HistoryPoint[] | null = null;

  for (const observation of observations) {
    if (observation.type !== history.type || observation.zone_code !== history.zone_code) continue;
    const time = Date.parse(observationTime(observation));
    if (!Number.isFinite(time) || time < from || time >= until || !Number.isFinite(observation.value)) continue;

    points ??= history.points.slice();
    const start = bucketStartMs(time, history.bucket_minutes, offset);
    // Les créneaux sont triés : la mesure tombe presque toujours dans le dernier.
    let index = points.length - 1;
    while (index >= 0 && Date.parse(points[index].time) > start) index--;
    const value = observation.value;
    const suspicious = observation.quality_status !== "normal" ? 1 : 0;
    const existing =
      index >= 0 && Math.abs(Date.parse(points[index].time) - start) < bucketMs / 2 ? points[index] : null;
    if (existing) {
      const count = existing.count + 1;
      points[index] = {
        ...existing,
        average: round2((existing.average * existing.count + value) / count),
        minimum: Math.min(existing.minimum, value),
        maximum: Math.max(existing.maximum, value),
        count,
        suspicious_count: existing.suspicious_count + suspicious,
      };
    } else {
      points.splice(index + 1, 0, {
        time: new Date(start).toISOString(),
        average: value,
        minimum: value,
        maximum: value,
        count: 1,
        suspicious_count: suspicious,
      });
    }
  }

  if (!points) return history;
  return { ...history, points, statistics: summarizePoints(points, tolerance) };
}

/**
 * Retire les créneaux entièrement antérieurs à `windowStart` (période
 * glissante). Retourne le même objet si rien n'a changé.
 */
export function trimHistory(history: ZoneHistory, windowStart: number, tolerance: number): ZoneHistory {
  if (!history.points.length) return history;
  const bucketMs = history.bucket_minutes * MINUTE_MS;
  const firstKept = history.points.findIndex((point) => Date.parse(point.time) + bucketMs > windowStart);
  if (firstKept === 0) return history;
  const points = firstKept < 0 ? [] : history.points.slice(firstKept);
  return { ...history, points, statistics: summarizePoints(points, tolerance) };
}
