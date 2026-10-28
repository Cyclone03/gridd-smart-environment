import { isDisplayMetric } from "../../constants/metrics";
import type { Zone } from "../../resources/zone";
import { formatTime, formatZoneType, zoneDisplayName } from "../../utils/format";
import { observationTime, readingKey, type LatestReadings } from "../../utils/observations";
import { MetricTile } from "./MetricTile";

/** Carte d'un espace : dernières mesures des capteurs réellement installés. */
export function ZoneCard({
  zone,
  latest,
  alertCount,
  onHistory,
}: {
  zone: Zone;
  latest: LatestReadings;
  alertCount: number;
  onHistory: () => void;
}) {
  const metrics = zone.metrics.filter(isDisplayMetric);
  const newest = metrics
    .map((type) => latest.get(readingKey(zone.code, type)))
    .filter((item) => item != null)
    .map(observationTime)
    .sort()
    .at(-1);

  return (
    <article className="zone-card">
      <div className="zone-card-head">
        <div>
          <span className="zone-type">{formatZoneType(zone.zone_type)}</span>
          <h3>{zoneDisplayName(zone)}</h3>
        </div>
        {alertCount > 0 && (
          <span className="zone-alert-count">
            {alertCount} alerte{alertCount > 1 ? "s" : ""}
          </span>
        )}
      </div>
      <div className="zone-metrics">
        {metrics.length ? (
          metrics.map((type) => (
            <MetricTile key={type} type={type} observation={latest.get(readingKey(zone.code, type))} />
          ))
        ) : (
          <p className="muted-note">Aucun capteur actif dans cet espace.</p>
        )}
      </div>
      <div className="zone-card-foot">
        <span>Dernière mesure : {formatTime(newest)}</span>
        <button type="button" onClick={onHistory}>
          Voir l’historique
        </button>
      </div>
    </article>
  );
}
