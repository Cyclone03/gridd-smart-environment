import { useDashboard } from "../../stores/dashboardStore";
import { formatDateTime, formatValue } from "../../utils/format";

export function OutdoorWeather({ compact = false }: { compact?: boolean }) {
  const { weatherSnapshot, weatherSnapshotLoading, weatherSnapshotError, weatherSnapshotDataInvalid } =
    useDashboard();
  const Heading = compact ? "h4" : "h3";

  return (
    <section className={`outdoor-weather${compact ? " compact" : ""}`} aria-label="Météo extérieure">
      <Heading>Météo extérieure</Heading>
      {weatherSnapshot ? (
        <>
          <div className="outdoor-weather-values">
            <p>
              <span>Température actuelle</span>
              <strong>{formatValue(weatherSnapshot.current_temperature_c, "temperature")} °C</strong>
            </p>
            <p>
              <span>Humidité actuelle</span>
              <strong>{formatValue(weatherSnapshot.current_relative_humidity_percent, "humidity")} %</strong>
            </p>
          </div>
          <small>Relevée à {formatDateTime(weatherSnapshot.current_at)}</small>
        </>
      ) : (
        <p className="muted-note" role={weatherSnapshotError || weatherSnapshotDataInvalid ? "alert" : "status"}>
          {weatherSnapshotError
            ? "Météo extérieure indisponible."
            : weatherSnapshotDataInvalid
              ? "Météo extérieure indisponible."
              : weatherSnapshotLoading
                ? "Chargement…"
                : "Indisponible"}
        </p>
      )}
    </section>
  );
}
