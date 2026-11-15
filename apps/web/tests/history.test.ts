import { describe, expect, it } from "vitest";
import type { ZoneHistory } from "../src/resources/history";
import type { Observation } from "../src/resources/observation";
import { bucketStartMs, mergeObservations, trimHistory, utcOffsetMinutes } from "../src/utils/history";

function base(): ZoneHistory {
  return {
    zone_code: "salle",
    type: "temperature",
    start: "2026-11-11T10:00:00-05:00",
    end: "2026-11-11T10:07:30-05:00",
    timezone: "America/Toronto",
    hours: 1,
    date: null,
    bucket_minutes: 5,
    unit: "°C",
    points: [
      { time: "2026-11-11T10:00:00-05:00", average: 20, minimum: 19, maximum: 21, count: 2, suspicious_count: 0 },
      { time: "2026-11-11T10:05:00-05:00", average: 22, minimum: 22, maximum: 22, count: 1, suspicious_count: 0 },
    ],
    statistics: { minimum: 19, maximum: 22, average: 20.67, count: 3, trend: "rising" },
  };
}

function observation(time: string, value: number, overrides: Partial<Observation> = {}): Observation {
  return {
    id: 1,
    zone: 1,
    zone_code: "salle",
    zone_name: "Salle",
    sensor: 1,
    sensor_node_id: "n1",
    type: "temperature",
    value,
    unit: "°C",
    observed_at: time,
    received_at: time,
    quality_status: "normal",
    quality_reason: "",
    ...overrides,
  };
}

describe("historique mis à jour en direct", () => {
  it("aligne les créneaux sur l'heure locale du serveur", () => {
    expect(utcOffsetMinutes("2026-11-11T10:00:00-05:00")).toBe(-300);
    expect(utcOffsetMinutes("2026-11-11T10:00:00+05:30")).toBe(330);
    expect(utcOffsetMinutes("2026-11-11T10:00:00Z")).toBe(0);
    // Créneaux de 3 h alignés sur minuit à Toronto (et non à Greenwich).
    const start = bucketStartMs(Date.parse("2026-11-11T10:20:00-05:00"), 180, -300);
    expect(new Date(start).toISOString()).toBe(new Date("2026-11-11T09:00:00-05:00").toISOString());
  });

  it("ajoute une mesure au créneau courant ou en crée un nouveau, et recalcule les statistiques", () => {
    const history = base();
    const merged = mergeObservations(history, [observation("2026-11-11T15:08:00Z", 25)], 0.2);
    expect(merged.points).toHaveLength(2);
    expect(merged.points[1]).toMatchObject({ average: 23.5, minimum: 22, maximum: 25, count: 2 });
    expect(merged.statistics).toEqual({ minimum: 19, maximum: 25, average: 21.75, count: 4, trend: "rising" });

    const next = mergeObservations(
      merged,
      [observation("2026-11-11T15:11:00Z", 18, { quality_status: "suspicious" })],
      0.2,
    );
    expect(next.points).toHaveLength(3);
    expect(Date.parse(next.points[2].time)).toBe(Date.parse("2026-11-11T10:10:00-05:00"));
    expect(next.points[2]).toMatchObject({ average: 18, count: 1, suspicious_count: 1 });
    expect(next.statistics.trend).toBe("falling");
  });

  it("ignore les mesures déjà comptées, d'une autre zone ou d'une autre mesure", () => {
    const history = base();
    const ignored = [
      observation("2026-11-11T15:07:00Z", 30), // antérieure à la fin de la requête
      observation("2026-11-11T15:09:00Z", 30, { zone_code: "autre" }),
      observation("2026-11-11T15:09:00Z", 30, { type: "humidity" }),
    ];
    expect(mergeObservations(history, ignored, 0.2)).toBe(history);
    // Période fixe : rien après sa fin.
    expect(mergeObservations(history, [observation("2026-11-11T15:09:00Z", 30)], 0.2, Date.parse(history.end))).toBe(
      history,
    );
  });

  it("retire les créneaux sortis d'une fenêtre glissante", () => {
    const history = base();
    expect(trimHistory(history, Date.parse("2026-11-11T10:04:00-05:00"), 0.2)).toBe(history);
    const trimmed = trimHistory(history, Date.parse("2026-11-11T10:05:00-05:00"), 0.2);
    expect(trimmed.points).toHaveLength(1);
    expect(trimmed.statistics).toEqual({ minimum: 22, maximum: 22, average: 22, count: 1, trend: "stable" });
  });
});
