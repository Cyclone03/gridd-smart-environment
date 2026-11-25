import { useState } from "react";
import { useNow } from "../../composables/useNow";
import {
  isClimatePredictionZoneCode,
  type ClimatePredictionZoneCode,
} from "../../resources/climatePrediction";
import type { Zone } from "../../resources/zone";
import { OutdoorWeather } from "./OutdoorWeather";
import { useDashboard } from "../../stores/dashboardStore";
import { formatDateTime, formatValue, zoneDisplayName } from "../../utils/format";
import { isFresh, readingKey } from "../../utils/observations";

export function ClimatePredictions() {
  const {
    zones,
    latest,
    climatePredictions,
    climatePredictionsLoading,
    climatePredictionsError,
    climatePredictionDataInvalid,
    status,
  } = useDashboard();
  const [selectedZoneCode, setSelectedZoneCode] = useState<ClimatePredictionZoneCode>("open-workspace");
  const now = useNow();
  const climateZones = zones.filter(
    (zone): zone is Zone & { code: ClimatePredictionZoneCode } => isClimatePredictionZoneCode(zone.code),
  );
  const selectedZone =
    climateZones.find((zone) => zone.code === selectedZoneCode) ?? climateZones[0];
  const prediction = selectedZone ? climatePredictions.get(selectedZone.code) : undefined;
  const upcomingPrediction = prediction && Date.parse(prediction.target_at) > now ? prediction : undefined;
  const temperature = selectedZone ? latest.get(readingKey(selectedZone.code, "temperature")) : undefined;
  const humidity = selectedZone ? latest.get(readingKey(selectedZone.code, "humidity")) : undefined;
  const temperatureIsCurrent = isFresh(temperature, now) && Number.isFinite(temperature.value);
  const humidityIsCurrent = isFresh(humidity, now) && Number.isFinite(humidity.value);
  return (
    <section className="climate-predictions" aria-labelledby="climate-predictions-title">
      <header className="climate-predictions-head">
        <div>
          <span className="section-kicker">Espace choisi</span>
          <h2 id="climate-predictions-title">Mesures et prévisions</h2>
        </div>
        <label className="prediction-zone-select">
          <span>Espace</span>
          <select
            aria-label="Espace pour les prévisions"
            value={selectedZone?.code ?? ""}
            onChange={(event) => {
              const nextZoneCode = event.target.value;
              if (isClimatePredictionZoneCode(nextZoneCode)) setSelectedZoneCode(nextZoneCode);
            }}
            disabled={climateZones.length === 0}
          >
            {climateZones.map((zone) => (
              <option key={zone.code} value={zone.code}>
                {zoneDisplayName(zone)}
              </option>
            ))}
          </select>
        </label>
      </header>

      {climatePredictionsError && (
        <p className="prediction-notice prediction-error" role="alert">
          Prévisions indisponibles.
          <span className="sr-only"> {climatePredictionsError}</span>
        </p>
      )}
      {status === "disconnected" && (
        <p className="prediction-notice" role="status">
          Connexion interrompue.
        </p>
      )}
      {climatePredictionDataInvalid && (
        <p className="prediction-notice prediction-error" role="alert">
          Prévision indisponible.
        </p>
      )}

      {!selectedZone ? (
        <p className="prediction-empty">Aucun espace disponible.</p>
      ) : (
        <>
          <h3 className="selected-prediction-zone">{zoneDisplayName(selectedZone)}</h3>
          <div className="prediction-values" aria-label="Mesures et prévisions">
            <article className="prediction-value">
              <span>Température mesurée</span>
              <strong>
                {temperatureIsCurrent ? `${formatValue(temperature.value, "temperature")} °C` : "—"}
              </strong>
              <small>{temperatureIsCurrent ? "Mesure réelle" : "Indisponible"}</small>
            </article>
            <article className="prediction-value predicted">
              <span>Température prévue</span>
              <strong>
                {upcomingPrediction ? `${formatValue(upcomingPrediction.predicted_temperature_c, "temperature")} °C` : "—"}
              </strong>
              <small>{upcomingPrediction ? "Prévision" : climatePredictionsLoading ? "Chargement…" : "Indisponible"}</small>
            </article>
            <article className="prediction-value">
              <span>Humidité mesurée</span>
              <strong>{humidityIsCurrent ? `${formatValue(humidity.value, "humidity")} %` : "—"}</strong>
              <small>{humidityIsCurrent ? "Mesure réelle" : "Indisponible"}</small>
            </article>
            <article className="prediction-value predicted">
              <span>Humidité prévue</span>
              <strong>
                {upcomingPrediction ? `${formatValue(upcomingPrediction.predicted_humidity_percent, "humidity")} %` : "—"}
              </strong>
              <small>{upcomingPrediction ? "Prévision" : climatePredictionsLoading ? "Chargement…" : "Indisponible"}</small>
            </article>
          </div>

          {upcomingPrediction && (
            <p className="prediction-target">
              Prévue pour <time dateTime={upcomingPrediction.target_at}>{formatDateTime(upcomingPrediction.target_at)}</time>
            </p>
          )}
        </>
      )}
      <OutdoorWeather />
    </section>
  );
}
