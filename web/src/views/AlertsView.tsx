import { AlertTriangle, Check, History, Settings2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { AlertItem } from "../components/alarms/AlertItem";
import { EmptyState, ErrorMessage, Loading } from "../components/common/Feedback";
import { PageHeader } from "../components/common/PageHeader";
import { ALERT_HISTORY_DAYS, ALERT_HISTORY_LIMIT, RESOLUTION_LABELS, SEVERITY_LABELS } from "../constants/alerts";
import { METRIC_VISUALS } from "../constants/metrics";
import { useAsyncData } from "../composables/useAsyncData";
import { routePath } from "../routes/definitions";
import { listAlarmRules } from "../services/alarmRulesService";
import { listAlerts } from "../services/alertsService";
import { useDashboard } from "../stores/dashboardStore";
import { daysAgo } from "../utils/dates";
import { alertOrigin, formatDateTime, zoneDisplayName } from "../utils/format";

/** Alertes actives, règles qui s'appliquent à un espace et historique récent. */
export function AlertsView() {
  const { alerts, zones, readAlertIds, markAlertRead, markAllAlertsRead, unreadAlertCount } = useDashboard();
  const [openAlert, setOpenAlert] = useState<number | null>(null);
  const [ruleZone, setRuleZone] = useState<string>("");
  const selectedZone = ruleZone || zones[0]?.code || "";

  const rules = useAsyncData(selectedZone ? (signal) => listAlarmRules({ zone: selectedZone }, signal) : null, [
    selectedZone,
  ]);
  // L'historique est rechargé quand la liste des alertes actives change.
  const events = useAsyncData(
    (signal) => listAlerts({ active: false, since: daysAgo(ALERT_HISTORY_DAYS), limit: ALERT_HISTORY_LIMIT }, signal),
    [alerts.map((alert) => alert.id).join(",")],
    { keepPrevious: true },
  );

  return (
    <main className="dashboard page-view">
      <PageHeader
        icon={AlertTriangle}
        overline="Alertes"
        title="Alertes actives et règles appliquées"
        description="Cliquez sur une alerte pour la consulter. Elle reste visible tant qu’elle est active."
        aside={
          <div className="alert-page-count">
            <span>
              {unreadAlertCount} non consultée{unreadAlertCount > 1 ? "s" : ""}
            </span>
            <strong>{alerts.length}</strong>
            <small>alertes actives</small>
          </div>
        }
      />
      <div className="alerts-layout">
        <section className="alerts-list-card">
          <div className="section-title">
            <div>
              <span className="section-kicker">En cours</span>
              <h2>Alertes actives</h2>
            </div>
            {unreadAlertCount > 0 && (
              <button type="button" className="read-all" onClick={markAllAlertsRead}>
                <Check size={15} /> Tout marquer consulté
              </button>
            )}
          </div>
          {alerts.length ? (
            alerts.map((alert) => (
              <AlertItem
                key={alert.id}
                alert={alert}
                read={readAlertIds.includes(alert.id)}
                open={openAlert === alert.id}
                onToggle={() => {
                  setOpenAlert(openAlert === alert.id ? null : alert.id);
                  markAlertRead(alert.id);
                }}
                onShowRules={() => setRuleZone(zones.find((zone) => zone.id === alert.zone)?.code ?? selectedZone)}
              />
            ))
          ) : (
            <EmptyState title="Aucune alerte active" />
          )}
        </section>
        <section className="rules-card">
          <div className="section-title">
            <div>
              <span className="section-kicker">Configuration</span>
              <h2>Règles appliquées</h2>
            </div>
            <Link className="secondary-button" to={routePath("alarmRules")}>
              <Settings2 size={15} aria-hidden="true" /> Gérer les règles
            </Link>
          </div>
          <label className="rule-select">
            Espace
            <select value={selectedZone} onChange={(event) => setRuleZone(event.target.value)}>
              {zones.map((zone) => (
                <option key={zone.code} value={zone.code}>
                  {zoneDisplayName(zone)}
                </option>
              ))}
            </select>
          </label>
          {rules.loading && !rules.data && <Loading />}
          {rules.error && <ErrorMessage onRetry={rules.reload}>{rules.error}</ErrorMessage>}
          {rules.data && (
            <ul className="compact-rules">
              {rules.data.length === 0 && <li className="muted-note">Aucune règle ne s’applique à cet espace.</li>}
              {rules.data.map((rule) => (
                <li key={rule.id} className={rule.enabled ? "" : "is-disabled"}>
                  <span style={{ color: METRIC_VISUALS[rule.metric].color }}>{METRIC_VISUALS[rule.metric].label}</span>
                  <strong>{rule.condition_label}</strong>
                  <small>
                    {rule.name} · {SEVERITY_LABELS[rule.severity]} · {rule.zone ? "cet espace" : "tous les espaces"}
                    {rule.enabled ? "" : " · inactive"}
                  </small>
                </li>
              ))}
            </ul>
          )}
          <div className="rules-note">
            <strong>Qualité des données (contrôlée par le serveur)</strong>
            <span>
              Limites physiques : température −20 à 60 °C · humidité 0 à 100 % · son 0 à 150 dBA · occupation 0 à 500.
              Une valeur hors limites est invalide et n’alimente pas les règles d’alarme. Une variation trop rapide ou
              une valeur inchangée trop longtemps est signalée comme suspecte.
            </span>
          </div>
        </section>
      </div>
      <section className="events-card">
        <div className="section-title">
          <div>
            <span className="section-kicker">
              <History size={13} aria-hidden="true" /> {ALERT_HISTORY_DAYS} derniers jours
            </span>
            <h2>Historique des déclenchements</h2>
          </div>
        </div>
        {events.error && <ErrorMessage onRetry={events.reload}>{events.error}</ErrorMessage>}
        {events.loading && !events.data && <Loading />}
        {events.data && events.data.length === 0 && <p className="muted-note">Aucune alerte résolue sur la période.</p>}
        {events.data && events.data.length > 0 && (
          <div className="table-scroll">
            <table className="events-table">
              <thead>
                <tr>
                  <th scope="col">Déclenchée</th>
                  <th scope="col">Résolue</th>
                  <th scope="col">Espace</th>
                  <th scope="col">Origine</th>
                  <th scope="col">Gravité</th>
                  <th scope="col">Résolution</th>
                </tr>
              </thead>
              <tbody>
                {events.data.map((event) => (
                  <tr key={event.id}>
                    <td>{formatDateTime(event.created_at)}</td>
                    <td>{event.resolved_at ? formatDateTime(event.resolved_at) : "—"}</td>
                    <td>{event.zone_name}</td>
                    <td title={event.message}>{alertOrigin(event)}</td>
                    <td className={`severity-text severity-${event.severity}`}>{SEVERITY_LABELS[event.severity]}</td>
                    <td>{RESOLUTION_LABELS[event.resolution] ?? event.resolution}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
