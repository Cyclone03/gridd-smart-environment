import { describe, expect, it } from "vitest";
import {
  mergeLatestClimatePredictions,
  parseClimatePredictionData,
} from "../src/resources/climatePrediction";
import { parseRealtimeMessage } from "../src/resources/realtime";
import { climatePrediction } from "./helpers";

const parse = (message: unknown) => parseRealtimeMessage(JSON.stringify(message));

describe("messages temps réel", () => {
  it("décode l'instantané et les changements avec leurs données", () => {
    const alerts = { active: [{ id: 1 }], history: [], history_days: 7 };
    expect(parse({ event: "dashboard.snapshot", data: { zones: [], latest: [], alerts } })).toEqual({
      event: "dashboard.snapshot",
      data: { zones: [], latest: [], alerts },
    });
    expect(parse({ event: "alerts.changed", data: alerts })).toEqual({ event: "alerts.changed", data: alerts });
    expect(parse({ event: "zones.changed", data: [{ code: "salle" }] })).toEqual({
      event: "zones.changed",
      data: [{ code: "salle" }],
    });
    expect(parse({ event: "observation.created", data: { id: 1 } })).toEqual({
      event: "observation.created",
      data: { id: 1 },
    });
    expect(parse({ event: "observations.created", data: [{ id: 1 }, { id: 2 }] })).toEqual({
      event: "observations.created",
      data: [{ id: 1 }, { id: 2 }],
    });
    expect(parse({ event: "observations.created", data: { id: 1 } })).toBeNull();
    expect(parse({ event: "dashboard.error", detail: "Base indisponible" })).toEqual({
      event: "dashboard.error",
      detail: "Base indisponible",
    });
    expect(parse({ event: "pong" })).toEqual({ event: "pong" });
  });

  it("ignore les messages incomplets, invalides ou retirés", () => {
    // Ancien format sans données : le client ne refait plus de requête HTTP.
    expect(parse({ event: "alerts.changed" })).toBeNull();
    expect(parse({ event: "dashboard.snapshot", data: { zones: [] } })).toBeNull();
    expect(parse({ event: "zones.changed", data: {} })).toBeNull();
    expect(parse({ event: "comfort.updated", data: {} })).toBeNull();
    expect(parse({ event: "energy.updated", data: {} })).toBeNull();
    expect(parseRealtimeMessage("pas du JSON")).toBeNull();
    expect(parse(null)).toBeNull();
  });

  it("valide le contrat de prédiction WebSocket et conserve ses champs", () => {
    const prediction = climatePrediction();
    expect(parse({ event: "climate_prediction.created", data: prediction })).toEqual({
      event: "climate_prediction.created",
      data: prediction,
    });
    expect(parseClimatePredictionData({ ...prediction, zone_code: "unknown-zone" })).toBeNull();
    expect(parseClimatePredictionData({ ...prediction, target_at: prediction.generated_at })).toBeNull();
    expect(parseClimatePredictionData({ ...prediction, predicted_temperature_c: Number.NaN })).toBeNull();
    expect(parseClimatePredictionData({ ...prediction, predicted_humidity_percent: "48" })).toBeNull();
    expect(
      parseClimatePredictionData({
        ...prediction,
        generated_at: "2026-11-15T18:00:00-05:00",
        target_at: "2026-11-15T19:00:00-05:00",
      }),
    ).toEqual({
      ...prediction,
      generated_at: "2026-11-15T18:00:00-05:00",
      target_at: "2026-11-15T19:00:00-05:00",
    });
    expect(parseClimatePredictionData({ ...prediction, generated_at: "2026-11-15T18:00:00" })).toBeNull();
    expect(parseClimatePredictionData({ ...prediction, prediction_mode: "test" })).toBeNull();
    expect(parse({ event: "climate_prediction.created", data: { ...prediction, model_version: "" } })).toBeNull();
  });

  it("déduplique par zone et ne remplace jamais une prédiction plus récente", () => {
    const known = climatePrediction();
    const index = new Map([[known.zone_code, known]]);
    const older = climatePrediction({
      prediction_id: 16,
      prediction_event_id: "8bf9c65f-11f0-40b5-aa63-471d4c262113",
      generated_at: new Date(Date.parse(known.generated_at) - 60_000).toISOString(),
    });
    const newer = climatePrediction({
      prediction_id: 18,
      prediction_event_id: "664c8b13-c0f1-4ca0-9e83-0b427d4e5cf7",
      generated_at: new Date(Date.parse(known.generated_at) + 60_000).toISOString(),
    });

    expect(mergeLatestClimatePredictions(index, [known, older])).toBe(index);
    const merged = mergeLatestClimatePredictions(index, [newer]);
    expect(merged.get(known.zone_code)).toEqual(newer);
    expect(index.get(known.zone_code)).toEqual(known);
  });
});
