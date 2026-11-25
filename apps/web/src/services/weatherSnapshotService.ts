import { request } from "../requests/httpClient";
import { parseWeatherSnapshotData, type WeatherSnapshot } from "../resources/weatherSnapshot";

/** Charge le dernier instantané météo persisté depuis l'API. */
export async function fetchLatestWeatherSnapshot(signal?: AbortSignal): Promise<WeatherSnapshot | null> {
  const response = await request<unknown>("/api/weather/latest/", { signal });
  if (response === null) return null;
  const snapshot = parseWeatherSnapshotData(response);
  if (!snapshot) throw new Error("La réponse du dernier instantané météo est invalide.");
  return snapshot;
}
