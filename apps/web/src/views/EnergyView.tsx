import { Flame, Gauge, Lightbulb, Snowflake, Zap } from "lucide-react";
import { ChartStatus } from "../components/charts/ChartStatus";
import { ErrorMessage, Loading } from "../components/common/Feedback";
import { PageHeader } from "../components/common/PageHeader";
import { SummaryCard } from "../components/common/SummaryCard";
import { EnergyBreakdownChart } from "../components/energy/EnergyBreakdownChart";
import { EnergySeriesChart } from "../components/energy/EnergySeriesChart";
import { EnergyZoneTable } from "../components/energy/EnergyZoneTable";
import { PeriodSelector } from "../components/forms/PeriodSelector";
import { ProfileForm } from "../components/forms/ProfileForm";
import { ENERGY_PROFILE_FIELDS } from "../constants/energy";
import { useAsyncData } from "../composables/useAsyncData";
import { useObservationPeriod } from "../composables/useObservationPeriod";
import { useProfileEditor } from "../composables/useProfileEditor";
import { useRevisionReload } from "../composables/useRevisionReload";
import { useZoneSelection } from "../composables/useZoneSelection";
import { sumEnergy, type EnergyProfile, type ZoneEnergyProfile } from "../resources/energy";
import {
  getEnergyProfile,
  getEnergySeries,
  getEnergySummary,
  resetEnergyProfile,
  updateEnergyProfile,
} from "../services/energyService";
import { useDashboard } from "../stores/dashboardStore";
import { capitalize, formatBucket, formatEnergy, formatPower, formatZoneType, zoneDisplayName } from "../utils/format";

/**
 * Consommation énergétique estimée : bilan par espace sur une période,
 * détail d'un espace et paramètres du modèle d'estimation.
 */
export function EnergyView() {
  const { zones, energyRevision } = useDashboard();
  const { period, resolved, apply, refresh } = useObservationPeriod();
  const start = resolved.start.getTime();
  const end = resolved.end.getTime();
  const range = { start: new Date(start), end: new Date(end) };
  const summary = useAsyncData((signal) => getEnergySummary(range, signal), [start, end], { keepPrevious: true });

  const visibleCodes = new Set(zones.map((zone) => zone.code));
  const zoneEnergy = (summary.data?.zones ?? []).filter((zone) => visibleCodes.has(zone.zone_code));
  const { zoneCode, select } = useZoneSelection(zoneEnergy.map((zone) => zone.zone_code));
  const series = useAsyncData(
    zoneCode ? (signal) => getEnergySeries(zoneCode, range, signal) : null,
    [zoneCode, start, end],
    { keepPrevious: true },
  );
  const editor = useProfileEditor<ZoneEnergyProfile, EnergyProfile>(zoneCode, {
    load: getEnergyProfile,
    save: updateEnergyProfile,
    reset: resetEnergyProfile,
  });

  // Nouvelles estimations reçues en temps réel : rechargement groupé.
  useRevisionReload(energyRevision, () => {
    if (resolved.live) refresh();
    else {
      summary.reload();
      series.reload();
    }
  });

  const total = sumEnergy(zoneEnergy);
  const selected = zoneEnergy.find((zone) => zone.zone_code === zoneCode);
  const spanMs = end - start;

  return (
    <main className="dashboard page-view">
      <PageHeader
        icon={Zap}
        overline="Énergie"
        title="Consommation énergétique estimée"
        description="Estimation par modèle à partir de la température et de l’occupation mesurées : aucune consommation n’est mesurée. Ajustez les paramètres de chaque espace pour la fiabiliser."
      />
      <PeriodSelector
        period={period}
        resolved={resolved}
        onApply={apply}
        onRefresh={() => (resolved.live ? refresh() : (summary.reload(), series.reload()))}
        busy={summary.loading}
      />
      {summary.error && <ErrorMessage onRetry={summary.reload}>{summary.error}</ErrorMessage>}
      {!summary.data && !summary.error && <Loading label="Calcul du bilan énergétique…" />}
      {summary.data && (
        <>
          <section className="summary-grid four-columns" aria-label="Bilan énergétique">
            <SummaryCard
              label="Énergie estimée"
              value={formatEnergy(total.total_kwh)}
              detail={capitalize(resolved.label)}
              icon={Zap}
              tone="green"
            />
            <SummaryCard
              label="Puissance moyenne"
              value={formatPower(total.average_power_w)}
              detail="tous espaces confondus"
              icon={Gauge}
              tone="violet"
            />
            <SummaryCard
              label="Chauffage et climatisation"
              value={formatEnergy(total.heating_kwh + total.cooling_kwh)}
              detail={`chauffage ${formatEnergy(total.heating_kwh)} · froid ${formatEnergy(total.cooling_kwh)}`}
              icon={total.cooling_kwh > total.heating_kwh ? Snowflake : Flame}
              tone="red"
            />
            <SummaryCard
              label="Éclairage et équipements"
              value={formatEnergy(total.lighting_kwh + total.equipment_kwh)}
              detail={`éclairage ${formatEnergy(total.lighting_kwh)}`}
              icon={Lightbulb}
              tone="amber"
            />
          </section>

          <section className="history-main energy-overview">
            <div className="section-bar flat">
              <div>
                <span className="section-kicker">Par espace</span>
                <h2>Répartition par usage</h2>
              </div>
            </div>
            {zoneEnergy.some((zone) => zone.total_kwh > 0) ? (
              <EnergyBreakdownChart zones={zoneEnergy} />
            ) : (
              <p className="muted-note padded">Aucune estimation pour cette période.</p>
            )}
            <EnergyZoneTable zones={zoneEnergy} selected={zoneCode} onSelect={select} />
          </section>
        </>
      )}

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
            <div className="current-reading">
              <span>Sur la période</span>
              <strong>{formatEnergy(selected.total_kwh)}</strong>
              <small>puissance moyenne {formatPower(selected.average_power_w)}</small>
            </div>
          </div>
          <section className="history-chart-card" aria-busy={series.loading}>
            <div className="chart-heading">
              <div>
                <span>Énergie estimée par usage</span>
                <strong>{capitalize(resolved.label)}</strong>
              </div>
              <small>{series.data ? `Créneaux de ${formatBucket(series.data.bucket_minutes)}` : " "}</small>
            </div>
            <div className="chart-wrap">
              <ChartStatus
                loading={series.loading}
                error={series.error}
                empty={!series.data?.points.length}
                onRetry={series.reload}
                emptyLabel="Aucune estimation pour cette période."
              />
              {!series.error && Boolean(series.data?.points.length) && (
                <EnergySeriesChart points={series.data!.points} spanMs={spanMs} />
              )}
            </div>
          </section>

          <section className="settings-card">
            <div>
              <span className="section-kicker">Modèle d’estimation</span>
              <h3>Paramètres de cet espace</h3>
              <p className="muted-note">
                Puissance = éclairage + équipements + chauffage ou climatisation (bilan entre déperditions, air neuf et
                apports internes). Les modifications s’appliquent aux estimations suivantes.
              </p>
            </div>
            {editor.error && <ErrorMessage onRetry={editor.reload}>{editor.error}</ErrorMessage>}
            {!editor.data && !editor.error && <Loading />}
            {editor.data && (
              <ProfileForm
                key={`${editor.data.zone_code}-${editor.version}`}
                label="Paramètres du modèle énergétique"
                fields={ENERGY_PROFILE_FIELDS}
                profile={editor.data.profile}
                customized={editor.data.customized}
                submitting={editor.submitting}
                serverMessage={editor.serverError?.message}
                serverErrors={editor.serverError?.fields}
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
