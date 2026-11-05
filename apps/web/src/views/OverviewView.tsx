import { Activity, Building2, Droplets, Thermometer, ThermometerSun, Users, Volume2, Zap } from "lucide-react";
import { SummaryCard } from "../components/common/SummaryCard";
import { SITE_LABEL } from "../constants/app";
import { DISPLAY_METRICS, METRIC_VISUALS } from "../constants/metrics";
import { useAsyncData } from "../composables/useAsyncData";
import { useRevisionReload } from "../composables/useRevisionReload";
import { sumEnergy } from "../resources/energy";
import { getEnergySummary } from "../services/energyService";
import { useDashboard } from "../stores/dashboardStore";
import { formatEnergy, formatLongDate, formatPower, formatTime, formatValue } from "../utils/format";
import { occupancyRate, soundComfortIndex } from "../utils/indicators";
import { averageLatest, readingKey } from "../utils/observations";

/** Vue d'ensemble : synthèse des dernières mesures de tous les espaces. */
export function OverviewView() {
  const { zones, latest, lastUpdate, comfort, energyRevision } = useDashboard();
  // Énergie estimée sur les dernières 24 h, recalculée à chaque rechargement.
  const energy = useAsyncData(
    (signal) => getEnergySummary({ start: new Date(Date.now() - 86_400_000), end: new Date() }, signal),
    [],
    { keepPrevious: true },
  );
  useRevisionReload(energyRevision, energy.reload, 60_000);
  const visibleCodes = new Set(zones.map((zone) => zone.code));
  const energyTotal = energy.data
    ? sumEnergy(energy.data.zones.filter((zone) => visibleCodes.has(zone.zone_code)))
    : null;
  const assessed = comfort.filter((zone) => zone.assessment && zone.assessment.level !== "unknown");
  const comfortable = assessed.filter((zone) => zone.assessment!.level === "comfortable").length;
  const scores = assessed.map((zone) => zone.assessment!.score).filter((score): score is number => score != null);
  const comfortScore = scores.length ? Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length) : null;
  const temperature = averageLatest(zones, latest, "temperature");
  const humidity = averageLatest(zones, latest, "humidity");
  const sound = averageLatest(zones, latest, "sound_level");
  const occupancy = averageLatest(zones, latest, "occupancy");
  const coverage = (stat: { count: number; expected: number }) => `${stat.count}/${stat.expected} espaces avec mesure`;

  return (
    <main className="dashboard">
      <header className="overview-head">
        <div>
          <span className="overline">
            <Activity size={15} aria-hidden="true" /> Vue d’ensemble
          </span>
          <h1>État environnemental du laboratoire</h1>
          <p>Synthèse des dernières mesures reçues.</p>
        </div>
        <div className="overview-context">
          <span>{SITE_LABEL}</span>
          <strong>{formatLongDate(new Date())}</strong>
          <small>Dernière mesure : {formatTime(lastUpdate)}</small>
        </div>
      </header>
      <section className="summary-grid three-columns" aria-label="Indicateurs">
        <SummaryCard
          label="Espaces suivis"
          value={String(zones.length)}
          detail="zones actives"
          icon={Building2}
          tone="green"
        />
        <SummaryCard
          label="Température moyenne"
          value={temperature.value == null ? "—" : `${formatValue(temperature.value, "temperature")} °C`}
          detail={coverage(temperature)}
          icon={Thermometer}
          tone="amber"
        />
        <SummaryCard
          label="Humidité moyenne"
          value={humidity.value == null ? "—" : `${formatValue(humidity.value, "humidity")} %`}
          detail={coverage(humidity)}
          icon={Droplets}
          tone="blue"
        />
        <SummaryCard
          label="Niveau sonore moyen"
          value={sound.value == null ? "—" : `${formatValue(sound.value, "sound_level")} dBA`}
          detail={coverage(sound)}
          icon={Volume2}
          tone="violet"
        />
        <SummaryCard
          label="Nombre de personnes dans le GRIDD"
          value={occupancy.value == null ? "—" : formatValue(occupancy.value, "occupancy")}
          detail={coverage(occupancy)}
          icon={Users}
          tone="red"
        />
        <SummaryCard
          label="Confort thermique"
          value={assessed.length ? `${comfortable}/${assessed.length} confortables` : "—"}
          detail={comfortScore == null ? "aucune évaluation" : `score moyen ${comfortScore}/100`}
          icon={ThermometerSun}
          tone="amber"
        />
        <SummaryCard
          label="Énergie estimée (24 h)"
          value={energyTotal ? formatEnergy(energyTotal.total_kwh) : "—"}
          detail={
            energyTotal ? `puissance moyenne ${formatPower(energyTotal.average_power_w)} · estimation` : "estimation"
          }
          icon={Zap}
          tone="green"
        />
        <SummaryCard
          label="Taux d'occupation"
          value={occupancy.value == null ? "—" : `${occupancyRate(occupancy.value)} %`}
          detail={coverage(occupancy)}
          icon={Users}
          tone="red"
        />
        <SummaryCard
          label="Indice de confort sonore"
          value={sound.value == null ? "—" : String(soundComfortIndex(sound.value))}
          detail={`${coverage(sound)} · indicatif`}
          icon={Volume2}
          tone="violet"
        />
      </section>
      <section className="availability-card">
        <div>
          <span className="section-kicker">Mesures reçues</span>
          <h2>Disponibilité par type de mesure</h2>
        </div>
        <div className="availability-grid">
          {DISPLAY_METRICS.map((type) => {
            const equipped = zones.filter((zone) => zone.metrics.includes(type));
            const count = equipped.filter((zone) => latest.has(readingKey(zone.code, type))).length;
            const Icon = METRIC_VISUALS[type].icon;
            return (
              <div key={type}>
                <Icon size={18} style={{ color: METRIC_VISUALS[type].color }} aria-hidden="true" />
                <span>{METRIC_VISUALS[type].label}</span>
                <strong>
                  {count}/{equipped.length}
                </strong>
              </div>
            );
          })}
        </div>
      </section>
    </main>
  );
}
