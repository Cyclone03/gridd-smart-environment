export const CLIMATE_PREDICTION_ZONE_CODES = [
  "open-workspace",
  "server-equipment-room",
  "professors-office",
  "individual-work-cubicle-01",
  "meeting-room",
  "individual-work-cubicle-02",
] as const;

export type ClimatePredictionZoneCode = (typeof CLIMATE_PREDICTION_ZONE_CODES)[number];
export type ClimatePredictionMode = "experimental" | "operational";

/** Reprend exactement le contenu de `data` de `climate_prediction.created`. */
export interface ClimatePrediction {
  prediction_id: number;
  prediction_event_id: string;
  zone_code: ClimatePredictionZoneCode;
  generated_at: string;
  target_at: string;
  predicted_temperature_c: number;
  predicted_humidity_percent: number;
  model_version: string;
  prediction_mode: ClimatePredictionMode;
}

const ISO_TIMESTAMP_WITH_OFFSET =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:(?:0\d|1[0-3]):[0-5]\d|14:00))$/;
const UUID = /^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i;

export function isClimatePredictionZoneCode(value: string): value is ClimatePredictionZoneCode {
  return CLIMATE_PREDICTION_ZONE_CODES.some((code) => code === value);
}

export function parseClimatePredictionData(value: unknown): ClimatePrediction | null {
  if (!isRecord(value)) return null;
  const {
    prediction_id,
    prediction_event_id,
    zone_code,
    generated_at,
    target_at,
    predicted_temperature_c,
    predicted_humidity_percent,
    model_version,
    prediction_mode,
  } = value;

  if (
    typeof prediction_id !== "number" ||
    !Number.isSafeInteger(prediction_id) ||
    prediction_id <= 0 ||
    typeof prediction_event_id !== "string" ||
    !UUID.test(prediction_event_id) ||
    typeof zone_code !== "string" ||
    !isClimatePredictionZoneCode(zone_code) ||
    !isIsoTimestampWithOffset(generated_at) ||
    !isIsoTimestampWithOffset(target_at) ||
    Date.parse(target_at) <= Date.parse(generated_at) ||
    typeof predicted_temperature_c !== "number" ||
    !Number.isFinite(predicted_temperature_c) ||
    typeof predicted_humidity_percent !== "number" ||
    !Number.isFinite(predicted_humidity_percent) ||
    typeof model_version !== "string" ||
    !model_version.trim() ||
    model_version.length > 255 ||
    (prediction_mode !== "experimental" && prediction_mode !== "operational")
  ) {
    return null;
  }

  return {
    prediction_id,
    prediction_event_id,
    zone_code,
    generated_at,
    target_at,
    predicted_temperature_c,
    predicted_humidity_percent,
    model_version: model_version.trim(),
    prediction_mode,
  };
}

export function mergeLatestClimatePredictions(
  current: ReadonlyMap<ClimatePredictionZoneCode, ClimatePrediction>,
  incoming: readonly ClimatePrediction[],
): ReadonlyMap<ClimatePredictionZoneCode, ClimatePrediction> {
  let next: Map<ClimatePredictionZoneCode, ClimatePrediction> | null = null;
  for (const prediction of incoming) {
    const known = (next ?? current).get(prediction.zone_code);
    if (
      known &&
      (prediction.prediction_event_id === known.prediction_event_id ||
        !isNewerPrediction(prediction, known))
    ) {
      continue;
    }
    next ??= new Map(current);
    next.set(prediction.zone_code, prediction);
  }
  return next ?? current;
}

export function isClimatePredictionEvent(raw: string): boolean {
  try {
    const message: unknown = JSON.parse(raw);
    return isRecord(message) && message.event === "climate_prediction.created";
  } catch {
    return false;
  }
}

function isIsoTimestampWithOffset(value: unknown): value is string {
  return (
    typeof value === "string" &&
    ISO_TIMESTAMP_WITH_OFFSET.test(value) &&
    Number.isFinite(Date.parse(value))
  );
}

function isNewerPrediction(candidate: ClimatePrediction, known: ClimatePrediction): boolean {
  const generatedDifference = Date.parse(candidate.generated_at) - Date.parse(known.generated_at);
  if (generatedDifference !== 0) return generatedDifference > 0;
  return candidate.prediction_id > known.prediction_id;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
