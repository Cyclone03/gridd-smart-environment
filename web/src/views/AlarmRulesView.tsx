import { BellRing, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { AlarmRuleList } from "../components/alarms/AlarmRuleList";
import { ErrorMessage, Loading } from "../components/common/Feedback";
import { PageHeader } from "../components/common/PageHeader";
import { METRIC_VISUALS } from "../constants/metrics";
import { useAlarmRules } from "../composables/useAlarmRules";
import type { MetricType } from "../resources/observation";
import { routePath } from "../routes/definitions";
import { useAuth } from "../stores/authStore";
import { useDashboard } from "../stores/dashboardStore";
import { zoneDisplayName } from "../utils/format";

type StatusFilter = "all" | "enabled" | "disabled";

/** Gestion des règles d'alarme : consultation pour tous, édition selon les droits. */
export function AlarmRulesView() {
  const { user, can } = useAuth();
  const { zones } = useDashboard();
  const { rules, loading, error, reload, actionError, pendingId, toggle, remove } = useAlarmRules();
  const [zoneFilter, setZoneFilter] = useState("");
  const [metricFilter, setMetricFilter] = useState<MetricType | "">("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const filtered = rules.filter(
    (rule) =>
      (!zoneFilter || (zoneFilter === "all" ? rule.zone === null : rule.zone === zoneFilter || rule.zone === null)) &&
      (!metricFilter || rule.metric === metricFilter) &&
      (statusFilter === "all" || (statusFilter === "enabled") === rule.enabled),
  );
  const enabledCount = rules.filter((rule) => rule.enabled).length;
  const metricsInUse = Array.from(new Set(rules.map((rule) => rule.metric)));

  return (
    <main className="dashboard page-view">
      <PageHeader
        icon={BellRing}
        overline="Alarmes"
        title="Règles d’alarme"
        description="Conditions évaluées par le serveur à chaque nouvelle mesure, que l’interface soit ouverte ou non."
        aside={
          can("alarm_rules.add") ? (
            <Link className="primary-button" to={routePath("alarmRuleCreate")}>
              <Plus size={16} aria-hidden="true" /> Nouvelle règle
            </Link>
          ) : !user ? (
            <Link className="secondary-button" to={`/login?next=${encodeURIComponent(routePath("alarmRules"))}`}>
              Se connecter pour modifier
            </Link>
          ) : (
            <span className="muted-note">Consultation seule : droits de gestion requis.</span>
          )
        }
      />
      <section className="rules-panel">
        <div className="section-bar">
          <div>
            <span className="section-kicker">
              {enabledCount} active{enabledCount > 1 ? "s" : ""} · {rules.length - enabledCount} inactive
              {rules.length - enabledCount > 1 ? "s" : ""}
            </span>
            <h2>Règles configurées</h2>
          </div>
          <div className="filters">
            <label className="field compact">
              <span>Espace</span>
              <select value={zoneFilter} onChange={(event) => setZoneFilter(event.target.value)}>
                <option value="">Tous</option>
                <option value="all">Règles globales uniquement</option>
                {zones.map((zone) => (
                  <option key={zone.code} value={zone.code}>
                    {zoneDisplayName(zone)}
                  </option>
                ))}
              </select>
            </label>
            <label className="field compact">
              <span>Paramètre</span>
              <select value={metricFilter} onChange={(event) => setMetricFilter(event.target.value as MetricType | "")}>
                <option value="">Tous</option>
                {metricsInUse.map((metric) => (
                  <option key={metric} value={metric}>
                    {METRIC_VISUALS[metric].label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field compact">
              <span>État</span>
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}>
                <option value="all">Toutes</option>
                <option value="enabled">Actives</option>
                <option value="disabled">Inactives</option>
              </select>
            </label>
          </div>
        </div>
        {actionError && <ErrorMessage>{actionError}</ErrorMessage>}
        {error && <ErrorMessage onRetry={reload}>{error}</ErrorMessage>}
        {loading && !rules.length && !error && <Loading label="Chargement des règles…" />}
        {!loading && !error && !rules.length && (
          <p className="muted-note padded">Aucune règle n’est configurée pour le moment.</p>
        )}
        {rules.length > 0 && !filtered.length && (
          <p className="muted-note padded">Aucune règle ne correspond aux filtres.</p>
        )}
        {filtered.length > 0 && (
          <AlarmRuleList
            rules={filtered}
            canChange={can("alarm_rules.change")}
            canDelete={can("alarm_rules.delete")}
            pendingId={pendingId}
            onToggle={toggle}
            onDelete={remove}
          />
        )}
      </section>
    </main>
  );
}
