import { Activity, Building2, Droplets, Thermometer, Volume2 } from "lucide-react";
import { SummaryCard } from "../components/common/SummaryCard";
import { ClimatePredictions } from "../components/dashboard/ClimatePredictions";
import { useNow } from "../composables/useNow";
import { SITE_LABEL } from "../constants/app";
import { DISPLAY_METRICS, isDisplayMetric, METRIC_VISUALS } from "../constants/metrics";
import { useDashboard } from "../stores/dashboardStore";
import { formatLongDate, formatReadingTime, formatValue } from "../utils/format";
import { soundComfortIndex } from "../utils/indicators";
import { averageLatest, isFresh, readingKey } from "../utils/observations";

/** Vue d'ensemble : synthèse des dernières mesures de tous les espaces. */
export function OverviewView() {
  const { zones, latest, lastUpdate } = useDashboard();
  const now = useNow();
  const visibleZones = zones.filter((zone) => zone.metrics.some(isDisplayMetric));
  // Seules les mesures à jour entrent dans les moyennes.
  const temperature = averageLatest(visibleZones, latest, "temperature", now);
  const humidity = averageLatest(visibleZones, latest, "humidity", now);
  const sound = averageLatest(visibleZones, latest, "sound_level", now);
  const coverage = (stat: { count: number; expected: number }) => `${stat.count}/${stat.expected} espaces à jour`;

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
          <small>Dernière mesure : {formatReadingTime(lastUpdate, new Date(now))}</small>
        </div>
      </header>
      <section className="summary-grid three-columns" aria-label="Indicateurs">
        <SummaryCard
          label="Espaces suivis"
          value={String(visibleZones.length)}
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
          label="Indice de confort sonore"
          value={sound.value == null ? "—" : String(soundComfortIndex(sound.value))}
          detail={`${coverage(sound)} · indicatif`}
          icon={Volume2}
          tone="violet"
        />
      </section>
      <section className="availability-card">
        <div>
          <span className="section-kicker">Mesures à jour</span>
          <h2>Disponibilité par type de mesure</h2>
        </div>
        <div className="availability-grid">
          {DISPLAY_METRICS.map((type) => {
            const equipped = visibleZones.filter((zone) => zone.metrics.includes(type));
            const count = equipped.filter((zone) => isFresh(latest.get(readingKey(zone.code, type)), now)).length;
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
      <ClimatePredictions />
    </main>
  );
}
