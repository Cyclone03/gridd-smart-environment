import { SmilePlus, ThermometerSun } from "lucide-react";
import { ChartStatus } from "../components/charts/ChartStatus";
import { ComfortHistoryChart } from "../components/comfort/ComfortHistoryChart";
import { ComfortZoneCard } from "../components/comfort/ComfortZoneCard";
import { ErrorMessage, Loading } from "../components/common/Feedback";
import { PageHeader } from "../components/common/PageHeader";
import { SummaryCard } from "../components/common/SummaryCard";
import { PeriodSelector } from "../components/forms/PeriodSelector";
import { ProfileForm } from "../components/forms/ProfileForm";
import { COMFORT_PROFILE_FIELDS } from "../constants/comfort";
import { useAsyncData } from "../composables/useAsyncData";
import { useObservationPeriod } from "../composables/useObservationPeriod";
import { useProfileEditor } from "../composables/useProfileEditor";
import { useZoneSelection } from "../composables/useZoneSelection";
import { comfortProfileErrors, type ComfortProfile, type ZoneComfort } from "../resources/comfort";
import {
  getComfortHistory,
  getComfortProfile,
  resetComfortProfile,
  updateComfortProfile,
} from "../services/comfortService";
import { useDashboard } from "../stores/dashboardStore";
import { capitalize, formatBucket, formatRatio, formatZoneType, zoneDisplayName } from "../utils/format";

/**
 * Confort thermique : niveau actuel de chaque espace (temps réel), historique
 * d'un espace et plages de confort utilisées pour l'évaluer.
 */
export function ComfortView() {
  const { comfort, loading, refresh } = useDashboard();
  const { zoneCode, select } = useZoneSelection(comfort.map((zone) => zone.zone_code));
  const { period, resolved, apply, refresh: refreshPeriod } = useObservationPeriod();
  const start = resolved.start.getTime();
  const end = resolved.end.getTime();
  const history = useAsyncData(
    zoneCode ? (signal) => getComfortHistory(zoneCode, { start: new Date(start), end: new Date(end) }, signal) : null,
    [zoneCode, start, end],
    { keepPrevious: true },
  );
  const editor = useProfileEditor<ZoneComfort, ComfortProfile>(zoneCode, {
    load: getComfortProfile,
    save: updateComfortProfile,
    reset: resetComfortProfile,
    onSaved: () => void refresh(),
  });

  if (loading && !comfort.length)
    return (
      <main className="dashboard page-view">
        <Loading label="Chargement du confort des espaces…" />
      </main>
    );

  const count = (level: string) => comfort.filter((zone) => zone.assessment?.level === level).length;
  const assessed = comfort.filter((zone) => zone.assessment && zone.assessment.level !== "unknown");
  const scores = assessed.map((zone) => zone.assessment!.score).filter((score): score is number => score != null);
  const averageScore = scores.length ? Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length) : null;
  const selected = comfort.find((zone) => zone.zone_code === zoneCode);
  const summary = history.data?.summary;

  return (
    <main className="dashboard page-view">
      <PageHeader
        icon={ThermometerSun}
        overline="Confort thermique"
        title="Confort des espaces"
        description="Évalué à chaque mesure de température ou d’humidité, selon les plages de confort de chaque espace."
      />
      <section className="summary-grid four-columns" aria-label="Synthèse du confort">
        <SummaryCard
          label="Espaces confortables"
          value={`${count("comfortable")}/${comfort.length}`}
          detail="dans leurs plages"
          icon={SmilePlus}
          tone="green"
        />
        <SummaryCard
          label="Acceptables"
          value={String(count("acceptable"))}
          detail="léger écart"
          icon={ThermometerSun}
          tone="amber"
        />
        <SummaryCard
          label="Inconfortables"
          value={String(count("uncomfortable"))}
          detail="écart marqué"
          icon={ThermometerSun}
          tone="red"
        />
        <SummaryCard
          label="Score moyen"
          value={averageScore == null ? "—" : `${averageScore}/100`}
          detail={`${assessed.length} espace${assessed.length > 1 ? "s" : ""} évalué${assessed.length > 1 ? "s" : ""}`}
          icon={SmilePlus}
          tone="blue"
        />
      </section>

      <section className="comfort-grid" aria-label="Confort actuel par espace">
        {comfort.map((zone) => (
          <ComfortZoneCard
            key={zone.zone_code}
            zone={zone}
            selected={zone.zone_code === zoneCode}
            onSelect={() => select(zone.zone_code)}
          />
        ))}
        {!comfort.length && <p className="muted-note">Aucun espace à évaluer.</p>}
      </section>

      {selected && (
        <section
          className="history-main detail-panel"
          aria-label={`Détail : ${zoneDisplayName({ code: selected.zone_code, name: selected.zone_name })}`}
        >
          <div className="history-title">
            <div>
              <span>{formatZoneType(selected.zone_type)}</span>
              <h2>{zoneDisplayName({ code: selected.zone_code, name: selected.zone_name })}</h2>
            </div>
          </div>
          <PeriodSelector
            period={period}
            resolved={resolved}
            onApply={apply}
            onRefresh={() => (resolved.live ? refreshPeriod() : history.reload())}
            busy={history.loading}
          />
          <section className="history-chart-card" aria-busy={history.loading}>
            <div className="chart-heading">
              <div>
                <span>Score et niveaux de confort</span>
                <strong>{capitalize(resolved.label)}</strong>
              </div>
              <small>{history.data ? `Créneaux de ${formatBucket(history.data.bucket_minutes)}` : " "}</small>
            </div>
            <div className="chart-wrap">
              <ChartStatus
                loading={history.loading}
                error={history.error}
                empty={!history.data?.points.length}
                onRetry={history.reload}
                emptyLabel="Aucune évaluation de confort pour cette période."
              />
              {!history.error && Boolean(history.data?.points.length) && (
                <ComfortHistoryChart points={history.data!.points} spanMs={end - start} />
              )}
            </div>
            <div className="history-stats">
              <div>
                <span>Score moyen</span>
                <strong>{summary?.average_score == null ? "—" : `${Math.round(summary.average_score)}/100`}</strong>
              </div>
              <div>
                <span>Confortable</span>
                <strong>{formatRatio(summary?.comfortable_ratio)}</strong>
              </div>
              <div>
                <span>Acceptable</span>
                <strong>{formatRatio(summary?.acceptable_ratio)}</strong>
              </div>
              <div>
                <span>Inconfortable</span>
                <strong>{formatRatio(summary?.uncomfortable_ratio)}</strong>
              </div>
            </div>
          </section>

          <section className="settings-card">
            <div>
              <span className="section-kicker">Plages de confort</span>
              <h3>Critères d’évaluation de cet espace</h3>
              <p className="muted-note">
                Confortable dans la plage, acceptable dans la tolérance, inconfortable au-delà. Les modifications
                s’appliquent aux mesures suivantes.
              </p>
            </div>
            {editor.error && <ErrorMessage onRetry={editor.reload}>{editor.error}</ErrorMessage>}
            {!editor.data && !editor.error && <Loading />}
            {editor.data && (
              <ProfileForm
                key={`${editor.data.zone_code}-${editor.version}`}
                label="Plages de confort"
                fields={COMFORT_PROFILE_FIELDS}
                profile={editor.data.profile}
                customized={editor.data.customized}
                submitting={editor.submitting}
                serverMessage={editor.serverError?.message}
                serverErrors={editor.serverError?.fields}
                cross={comfortProfileErrors}
                onSubmit={(values) => void editor.save(values)}
                onReset={() => void editor.reset()}
              />
            )}
          </section>
        </section>
      )}
    </main>
  );
}
