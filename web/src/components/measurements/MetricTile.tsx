import { METRIC_UNITS, METRIC_VISUALS } from "../../constants/metrics";
import type { MetricType, Observation } from "../../resources/observation";
import { formatTime, formatValue } from "../../utils/format";
import { observationTime } from "../../utils/observations";

/** Dernière valeur d'une mesure ; « — » tant qu'aucune mesure n'est reçue. */
export function MetricTile({ type, observation }: { type: MetricType; observation?: Observation }) {
  const metric = METRIC_VISUALS[type];
  const Icon = metric.icon;
  return (
    <div className={`metric-tile ${observation ? "" : "metric-missing"}`}>
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
          <time dateTime={observationTime(observation)}>Mesuré à {formatTime(observationTime(observation))}</time>
        )}
      </div>
    </div>
  );
}
