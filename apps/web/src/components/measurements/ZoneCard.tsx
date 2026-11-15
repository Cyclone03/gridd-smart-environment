import { useNow } from "../../composables/useNow";
import { STALE_READING_MS } from "../../constants/app";
import { isDisplayMetric } from "../../constants/metrics";
import type { Zone } from "../../resources/zone";
import { formatReadingTime, formatZoneType, zoneDisplayName } from "../../utils/format";
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
  const now = useNow();
  // Plus aucune mesure récente dans cet espace : capteurs muets ou données
  // qui n'arrivent plus au serveur.
  const silent = newest != null && now - Date.parse(newest) > STALE_READING_MS;

  return (
    <article className="zone-card">
      <div className="zone-card-head">
        <div>
          <span className="zone-type">{formatZoneType(zone.zone_type)}</span>
          <h3>{zoneDisplayName(zone)}</h3>
        </div>
        {(alertCount > 0 || silent) && (
          <div className="zone-card-badges">
            {silent && <span className="zone-stale-badge">Pas de données récentes</span>}
            {alertCount > 0 && (
              <span className="zone-alert-count">
                {alertCount} alerte{alertCount > 1 ? "s" : ""}
              </span>
            )}
          </div>
        )}
      </div>
      <div className="zone-metrics">
        {metrics.length ? (
          metrics.map((type) => (
            <MetricTile key={type} type={type} observation={latest.get(readingKey(zone.code, type))} now={now} />
          ))
        ) : (
          <p className="muted-note">Aucun capteur actif dans cet espace.</p>
        )}
      </div>
      <div className="zone-card-foot">
        <span>Dernière mesure : {formatReadingTime(newest, new Date(now))}</span>
        <button type="button" onClick={onHistory}>
          Voir l’historique
        </button>
      </div>
    </article>
  );
}
