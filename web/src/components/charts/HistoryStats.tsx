import type { ZoneHistory } from "../../resources/history";
import type { MetricType } from "../../resources/observation";
import { formatValue } from "../../utils/format";
import { naiveNextValue } from "../../utils/prediction";

const TREND_LABELS = { rising: "En hausse", falling: "En baisse", stable: "Stable" } as const;

/** Statistiques de la période affichée. */
export function HistoryStats({ history, metric }: { history: ZoneHistory | null; metric: MetricType }) {
  const stats = history?.statistics;
  const withUnit = (value: number | null | undefined) =>
    value != null && history ? `${formatValue(value, metric)} ${history.unit}` : "—";
  const trend = stats && stats.count > 0 ? stats.trend : null;
  const projection = naiveNextValue(history?.points.at(-1)?.average, metric, trend);

  return (
    <div className="history-stats">
      <div>
        <span>Moyenne</span>
        <strong>{withUnit(stats?.average)}</strong>
      </div>
      <div>
        <span>Minimum</span>
        <strong>{withUnit(stats?.minimum)}</strong>
      </div>
      <div>
        <span>Maximum</span>
        <strong>{withUnit(stats?.maximum)}</strong>
      </div>
      <div>
        <span>Mesures</span>
        <strong>{stats?.count ?? 0}</strong>
      </div>
      <div>
        <span>Tendance</span>
        <strong>{trend ? TREND_LABELS[trend] : "—"}</strong>
      </div>
      <div title="Extrapolation indicative : dernière moyenne ajustée selon la tendance.">
        <span>Prochaine valeur (indicative)</span>
        <strong>{withUnit(projection)}</strong>
      </div>
    </div>
  );
}
