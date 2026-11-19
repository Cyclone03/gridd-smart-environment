/** Instantané Open-Meteo diffusé sur le WebSocket et exposé par l'API. */
export interface WeatherSnapshot {
  weather_snapshot_id: number;
  weather_snapshot_event_id: string;
  generated_at: string;
  provider: "open-meteo";
  current_at: string;
  current_temperature_c: number;
  current_relative_humidity_percent: number;
  forecast_h1_at: string;
  forecast_h1_temperature_c: number;
  forecast_h1_relative_humidity_percent: number;
}

const ISO_TIMESTAMP_WITH_OFFSET =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:(?:0\d|1[0-3]):[0-5]\d|14:00))$/;
const UUID = /^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i;

export function parseWeatherSnapshotData(value: unknown): WeatherSnapshot | null {
  if (!isRecord(value)) return null;
  const {
    weather_snapshot_id,
    weather_snapshot_event_id,
    generated_at,
    provider,
    current_at,
    current_temperature_c,
    current_relative_humidity_percent,
    forecast_h1_at,
    forecast_h1_temperature_c,
    forecast_h1_relative_humidity_percent,
  } = value;

  if (
    typeof weather_snapshot_id !== "number" ||
    !Number.isSafeInteger(weather_snapshot_id) ||
    weather_snapshot_id <= 0 ||
    typeof weather_snapshot_event_id !== "string" ||
    !UUID.test(weather_snapshot_event_id) ||
    !isTimestamp(generated_at) ||
    provider !== "open-meteo" ||
    !isTimestamp(current_at) ||
    !isTimestamp(forecast_h1_at) ||
    Date.parse(forecast_h1_at) <= Date.parse(current_at) ||
    Date.parse(forecast_h1_at) <= Date.parse(generated_at) ||
    !isFiniteNumber(current_temperature_c) ||
    !isHumidity(current_relative_humidity_percent) ||
    !isFiniteNumber(forecast_h1_temperature_c) ||
    !isHumidity(forecast_h1_relative_humidity_percent)
  ) {
    return null;
  }

  return {
    weather_snapshot_id,
    weather_snapshot_event_id,
    generated_at,
    provider,
    current_at,
    current_temperature_c,
    current_relative_humidity_percent,
    forecast_h1_at,
    forecast_h1_temperature_c,
    forecast_h1_relative_humidity_percent,
  };
}

export function isWeatherSnapshotEvent(raw: string): boolean {
  try {
    const message: unknown = JSON.parse(raw);
    return isRecord(message) && message.event === "weather_snapshot.created";
  } catch {
    return false;
  }
}

export function mergeLatestWeatherSnapshot(
  current: WeatherSnapshot | null,
  candidate: WeatherSnapshot | null,
): WeatherSnapshot | null {
  if (!candidate) return current;
  if (!current) return candidate;
  const generatedDifference = Date.parse(candidate.generated_at) - Date.parse(current.generated_at);
  if (generatedDifference !== 0) return generatedDifference > 0 ? candidate : current;
  return candidate.weather_snapshot_id > current.weather_snapshot_id ? candidate : current;
}

function isTimestamp(value: unknown): value is string {
  return (
    typeof value === "string" &&
    ISO_TIMESTAMP_WITH_OFFSET.test(value) &&
    Number.isFinite(Date.parse(value))
  );
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isHumidity(value: unknown): value is number {
  return isFiniteNumber(value) && value >= 0 && value <= 100;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
