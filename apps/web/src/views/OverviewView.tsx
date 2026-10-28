import { Activity, Building2, Droplets, Gauge, Thermometer, Users, Volume2 } from "lucide-react";
import { SummaryCard } from "../components/common/SummaryCard";
import { SITE_LABEL } from "../constants/app";
import { DISPLAY_METRICS, METRIC_VISUALS } from "../constants/metrics";
import { useDashboard } from "../stores/dashboardStore";
import { occupancyRate, soundComfortIndex, thermalComfortIndex } from "../utils/comfort";
import { formatLongDate, formatTime, formatValue } from "../utils/format";
import { averageLatest, readingKey } from "../utils/observations";

/** Vue d'ensemble : synthèse des dernières mesures de tous les espaces. */
export function OverviewView() {
  const { zones, latest, lastUpdate } = useDashboard();
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
          label="Indice de confort thermique"
          value={
            temperature.value == null || humidity.value == null
              ? "—"
              : String(thermalComfortIndex(temperature.value, humidity.value))
          }
          detail={`${coverage(temperature)} · indicatif`}
          icon={Gauge}
          tone="amber"
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
