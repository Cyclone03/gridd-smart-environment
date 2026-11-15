import { METRIC_UNITS, METRIC_VISUALS } from "../../constants/metrics";
import type { MetricType, Observation } from "../../resources/observation";
import { formatReadingTime, formatSince, formatValue } from "../../utils/format";
import { isFresh, observationTime } from "../../utils/observations";

/**
 * Dernière valeur d'une mesure ; « — » tant qu'aucune mesure n'est reçue.
 * Une valeur ancienne reste affichée mais est signalée comme n'étant plus à jour.
 */
export function MetricTile({ type, observation, now }: { type: MetricType; observation?: Observation; now: number }) {
  const metric = METRIC_VISUALS[type];
  const Icon = metric.icon;
  const stale = observation != null && !isFresh(observation, now);
  const at = observation ? observationTime(observation) : "";
  return (
    <div className={`metric-tile ${observation ? "" : "metric-missing"} ${stale ? "metric-stale" : ""}`}>
      <div className="metric-icon" style={{ color: metric.color }}>
        <Icon size={17} aria-hidden="true" />
      </div>
      <div>
        <span>{metric.shortLabel}</span>
        <strong>
          {observation ? formatValue(observation.value, type) : "—"}
          {observation && <small>{METRIC_UNITS[type]}</small>}
        </strong>
        {observation && (
          <time dateTime={observationTime(observation)}>
            {stale
              ? `Aucune mesure depuis ${formatSince(at, new Date(now))}`
              : `Mesuré à ${formatReadingTime(at, new Date(now))}`}
          </time>
        )}
      </div>
    </div>
  );
}
