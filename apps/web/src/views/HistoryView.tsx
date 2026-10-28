import { CalendarDays, ChevronRight } from "lucide-react";
import { CorrelationPanel } from "../components/charts/correlation/CorrelationPanel";
import { ChartStatus } from "../components/charts/ChartStatus";
import { HistoryChart } from "../components/charts/HistoryChart";
import { HistoryStats } from "../components/charts/HistoryStats";
import { Loading } from "../components/common/Feedback";
import { PageHeader } from "../components/common/PageHeader";
import { PeriodSelector } from "../components/forms/PeriodSelector";
import { CORRELATION_METRICS, METRIC_UNITS, METRIC_VISUALS } from "../constants/metrics";
import { useCorrelationSeries } from "../composables/useCorrelationSeries";
import { useHistoryFilters } from "../composables/useHistoryFilters";
import { useObservationPeriod } from "../composables/useObservationPeriod";
import { useZoneHistory } from "../composables/useZoneHistory";
import { useDashboard } from "../stores/dashboardStore";
import { capitalize, formatBucket, formatTime, formatValue, formatZoneType, zoneDisplayName } from "../utils/format";
import { observationTime, readingKey } from "../utils/observations";

/**
 * Analyse historique : choix de l'espace, de la mesure et de la période
 * d'observation, courbe agrégée, statistiques et corrélations.
 */
export function HistoryView() {
  const { zones, latest, loading: dashboardLoading } = useDashboard();
  const { zone, metric, availableMetrics, selectZone, selectMetric } = useHistoryFilters(zones);
  const { period, resolved, apply, refresh } = useObservationPeriod();
  const history = useZoneHistory(zone?.code ?? null, metric, resolved);
  const correlationSupported = CORRELATION_METRICS.filter((item) => zone?.metrics.includes(item)).length >= 2;
  const correlation = useCorrelationSeries(zone?.code ?? null, zone?.metrics ?? [], resolved);

  if (dashboardLoading && !zones.length)
    return (
      <main className="dashboard page-view">
        <Loading label="Chargement des espaces…" />
      </main>
    );

  const current = zone ? latest.get(readingKey(zone.code, metric)) : undefined;
  const points = history.data?.points ?? [];
  const spanMs = resolved.end.getTime() - resolved.start.getTime();

  return (
    <main className="dashboard page-view">
      <PageHeader
        icon={CalendarDays}
        overline="Analyse historique"
        title="Historique par espace"
        description="Choisissez un espace, une mesure et une période d’observation."
      />
      <section className="history-workspace">
        <aside className="space-selector" aria-label="Sélectionner un espace">
          <span className="section-kicker">Espaces suivis</span>
          {zones.map((item) => {
            const available = item.metrics.filter((type) => latest.has(readingKey(item.code, type))).length;
            return (
              <button
                key={item.code}
                type="button"
                className={zone?.code === item.code ? "active" : ""}
                aria-pressed={zone?.code === item.code}
                onClick={() => selectZone(item.code)}
              >
                <span>{zoneDisplayName(item)}</span>
                <small>
                  {formatZoneType(item.zone_type)} · {available}/{item.metrics.length} mesures reçues
                </small>
                <ChevronRight size={16} aria-hidden="true" />
              </button>
            );
          })}
        </aside>
        <div className="history-main">
          {!zone ? (
            <p className="muted-note">Aucun espace disponible.</p>
          ) : (
            <>
              <div className="history-title">
                <div>
                  <span>{formatZoneType(zone.zone_type)}</span>
                  <h2>{zoneDisplayName(zone)}</h2>
                </div>
                <div className="current-reading">
                  <span>Dernière mesure reçue</span>
                  <strong>{current ? `${formatValue(current.value, metric)} ${METRIC_UNITS[metric]}` : "—"}</strong>
                  <small>{current ? formatTime(observationTime(current)) : "Aucune mesure"}</small>
                </div>
              </div>
              <div className="metric-tabs" role="tablist" aria-label="Mesure">
                {availableMetrics.map((type) => {
                  const Icon = METRIC_VISUALS[type].icon;
                  return (
                    <button
                      type="button"
                      role="tab"
                      aria-selected={metric === type}
                      key={type}
                      className={metric === type ? "active" : ""}
                      onClick={() => selectMetric(type)}
                    >
                      <Icon size={16} aria-hidden="true" />
                      {METRIC_VISUALS[type].label}
                      <i className={latest.has(readingKey(zone.code, type)) ? "available" : "missing"} />
                    </button>
                  );
                })}
              </div>
              <PeriodSelector
                period={period}
                resolved={resolved}
                onApply={apply}
                onRefresh={() => {
                  // Une période glissante est recalculée (nouvelles bornes) ;
                  // une période fixe est simplement rechargée.
                  if (resolved.live) refresh();
                  else {
                    history.reload();
                    correlation.reload();
                  }
                }}
                busy={history.loading}
              />
              <section className="history-chart-card" aria-busy={history.loading}>
                <div className="chart-heading">
                  <div>
                    <span>{METRIC_VISUALS[metric].label}</span>
                    <strong>{capitalize(resolved.label)}</strong>
                  </div>
                  <small>
                    {history.data ? `Moyennes par créneau de ${formatBucket(history.data.bucket_minutes)}` : " "}
                    {history.loading && history.data ? " · actualisation…" : ""}
                  </small>
                </div>
                <div className="chart-wrap">
                  <ChartStatus
                    loading={history.loading}
                    error={history.error}
                    empty={!points.length}
                    onRetry={history.reload}
                  />
                  {!history.error && points.length > 0 && (
                    <HistoryChart points={points} metric={metric} unit={history.data?.unit ?? ""} spanMs={spanMs} />
                  )}
                </div>
                <HistoryStats history={history.data} metric={metric} />
              </section>
              <CorrelationPanel
                zoneName={zoneDisplayName(zone)}
                supported={correlationSupported}
                period={resolved}
                series={correlation.data}
                loading={correlation.loading}
                error={correlation.error}
                onRetry={correlation.reload}
              />
            </>
          )}
        </div>
      </section>
    </main>
  );
}
