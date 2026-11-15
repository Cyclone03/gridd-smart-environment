import { CalendarDays, ChevronRight } from "lucide-react";
import { useMemo } from "react";
import { CorrelationPanel } from "../components/charts/correlation/CorrelationPanel";
import { ChartStatus } from "../components/charts/ChartStatus";
import { HistoryChart } from "../components/charts/HistoryChart";
import { HistoryStats } from "../components/charts/HistoryStats";
import { Loading } from "../components/common/Feedback";
import { PageHeader } from "../components/common/PageHeader";
import { PeriodSelector } from "../components/forms/PeriodSelector";
import { CORRELATION_METRICS, METRIC_UNITS, METRIC_VISUALS } from "../constants/metrics";
import { useHistoryFilters } from "../composables/useHistoryFilters";
import { useLiveHistories } from "../composables/useLiveHistories";
import { useNow } from "../composables/useNow";
import { useObservationPeriod } from "../composables/useObservationPeriod";
import { useDashboard } from "../stores/dashboardStore";
import { MIN_POINTS, toSeries } from "../utils/correlation";
import {
  capitalize,
  formatBucket,
  formatReadingTime,
  formatSince,
  formatValue,
  formatZoneType,
  zoneDisplayName,
} from "../utils/format";
import { isFresh, observationTime, readingKey } from "../utils/observations";

/**
 * Analyse historique : choix de l'espace, de la mesure et de la période
 * d'observation, courbe agrégée, statistiques et corrélations.
 *
 * L'historique est chargé une fois par sélection, puis complété en direct
 * par les mesures reçues sur le WebSocket (aucun rechargement périodique).
 */
export function HistoryView() {
  const { zones, latest, loading: dashboardLoading } = useDashboard();
  const { zone, metric, availableMetrics, selectZone, selectMetric } = useHistoryFilters(zones);
  const { period, resolved, window: shown, apply, refresh } = useObservationPeriod();

  const correlationMetrics = CORRELATION_METRICS.filter((item) => zone?.metrics.includes(item));
  const correlationSupported = correlationMetrics.length >= 2;
  // Deux chargements indépendants : les mesures de corrélation (partagées
  // avec le graphique) et, si besoin, la mesure affichée hors corrélation.
  // Passer d'un onglet à une mesure déjà chargée ne relance aucune requête.
  const inCorrelation = correlationSupported && correlationMetrics.includes(metric as never);
  const correlationLive = useLiveHistories(
    zone?.code ?? null,
    correlationSupported ? correlationMetrics : [],
    resolved,
    shown,
  );
  const metricLive = useLiveHistories(zone?.code ?? null, inCorrelation ? [] : [metric], resolved, shown);
  const live = inCorrelation ? correlationLive : metricLive;
  const historyData = live.histories[metric] ?? null;
  const historyError = live.error ?? live.errors[metric] ?? null;

  // Tableau de taille fixe (une entrée par mesure de corrélation) : la
  // mémorisation ne dépend que des historiques réellement modifiés.
  const correlationHistories = CORRELATION_METRICS.map((item) =>
    correlationMetrics.includes(item) ? correlationLive.histories[item] : undefined,
  );
  const series = useMemo(() => {
    if (!correlationSupported) return null;
    const loaded = CORRELATION_METRICS.flatMap((item, index) => {
      const history = correlationHistories[index];
      return history ? [toSeries(history, item)] : [];
    });
    if (loaded.length < correlationMetrics.length) return null;
    return loaded.filter((item) => item.values.size >= MIN_POINTS);
  }, [correlationSupported, correlationMetrics.length, ...correlationHistories]);
  const now = useNow();
  const correlationError =
    correlationLive.error ?? correlationMetrics.map((item) => correlationLive.errors[item]).find(Boolean) ?? null;

  if (dashboardLoading && !zones.length)
    return (
      <main className="dashboard page-view">
        <Loading label="Chargement des espaces…" />
      </main>
    );

  const current = zone ? latest.get(readingKey(zone.code, metric)) : undefined;
  const currentStale = current != null && !isFresh(current, now);
  const currentTime = current ? formatReadingTime(observationTime(current), new Date(now)) : "";
  const currentSince = current ? formatSince(observationTime(current), new Date(now)) : "";
  // Période vide alors que le capteur a déjà mesuré : le dire, plutôt qu'un
  // graphique vide qui semble « ne pas charger ».
  const emptyLabel =
    current && Date.parse(observationTime(current)) < shown.start.getTime()
      ? `Aucune mesure sur cette période. Dernière mesure reçue ${currentSince} — ce capteur n’envoie plus de données (ou elles n’arrivent plus au serveur).`
      : undefined;
  const points = historyData?.points ?? [];
  const spanMs = shown.end.getTime() - shown.start.getTime();

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
            const readings = item.metrics.map((type) => latest.get(readingKey(item.code, type)));
            const fresh = readings.filter((reading) => isFresh(reading, now)).length;
            const newest = readings
              .filter((reading) => reading != null)
              .map(observationTime)
              .sort()
              .at(-1);
            return (
              <button
                key={item.code}
                type="button"
                className={zone?.code === item.code ? "active" : ""}
                aria-pressed={zone?.code === item.code}
                onClick={() => selectZone(item.code)}
              >
                <span>{zoneDisplayName(item)}</span>
                {fresh === 0 && newest ? (
                  <small className="stale">
                    {formatZoneType(item.zone_type)} · aucune donnée depuis {formatSince(newest, new Date(now))}
                  </small>
                ) : (
                  <small>
                    {formatZoneType(item.zone_type)} · {fresh}/{item.metrics.length} mesures à jour
                  </small>
                )}
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
                  <small className={currentStale ? "stale" : undefined}>
                    {current ? (currentStale ? `Aucune mesure depuis ${currentSince}` : currentTime) : "Aucune mesure"}
                  </small>
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
                resolved={shown}
                onApply={apply}
                onRefresh={() => {
                  // Une période glissante est recalculée (nouvelles bornes) ;
                  // une période fixe est simplement rechargée.
                  if (resolved.live) refresh();
                  else {
                    correlationLive.reload();
                    metricLive.reload();
                  }
                }}
                busy={live.loading}
              />
              <section className="history-chart-card" aria-busy={live.loading}>
                <div className="chart-heading">
                  <div>
                    <span>{METRIC_VISUALS[metric].label}</span>
                    <strong>{capitalize(shown.label)}</strong>
                  </div>
                  <small>
                    {historyData ? `Moyennes par créneau de ${formatBucket(historyData.bucket_minutes)}` : " "}
                    {live.loading && historyData ? " · actualisation…" : ""}
                  </small>
                </div>
                <div className="chart-wrap">
                  <ChartStatus
                    loading={live.loading}
                    error={historyError}
                    empty={!points.length}
                    onRetry={live.reload}
                    emptyLabel={emptyLabel}
                  />
                  {!historyError && points.length > 0 && (
                    <HistoryChart points={points} metric={metric} unit={historyData?.unit ?? ""} spanMs={spanMs} />
                  )}
                </div>
                <HistoryStats history={historyData} metric={metric} />
              </section>
              <CorrelationPanel
                zoneName={zoneDisplayName(zone)}
                supported={correlationSupported}
                period={shown}
                series={series}
                loading={correlationLive.loading}
                error={correlationError}
                onRetry={correlationLive.reload}
              />
            </>
          )}
        </div>
      </section>
    </main>
  );
}
