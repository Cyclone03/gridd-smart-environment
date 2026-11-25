import { request } from "../requests/httpClient";
import { parseClimatePredictionData, type ClimatePrediction } from "../resources/climatePrediction";

export interface LatestClimatePredictions {
  predictions: ClimatePrediction[];
  invalidCount: number;
}

/** Charge l'instantané persistant des prédictions depuis l'API en lecture seule. */
export async function fetchLatestClimatePredictions(signal?: AbortSignal): Promise<LatestClimatePredictions> {
  const response = await request<unknown>("/api/climate-predictions/latest/", { signal });
  if (!Array.isArray(response)) {
    throw new Error("La réponse des prédictions climatiques doit être un tableau.");
  }

  const predictions: ClimatePrediction[] = [];
  let invalidCount = 0;
  for (const item of response) {
    const prediction = parseClimatePredictionData(item);
    if (prediction) predictions.push(prediction);
    else invalidCount += 1;
  }
  return { predictions, invalidCount };
}
