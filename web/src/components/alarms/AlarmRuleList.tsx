import { BellOff, BellRing, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { SEVERITY_LABELS } from "../../constants/alerts";
import { METRIC_VISUALS } from "../../constants/metrics";
import type { AlarmRule } from "../../resources/alarmRule";
import { routePath } from "../../routes/definitions";
import { formatDuration } from "../../utils/format";

/**
 * Liste des règles. Chaque règle affiche explicitement le paramètre, la
 * condition, le seuil, l'unité, l'espace et le comportement (durée,
 * hystérésis, gravité). Les actions dépendent des droits de l'utilisateur.
 */
export function AlarmRuleList({
  rules,
  canChange,
  canDelete,
  pendingId,
  onToggle,
  onDelete,
}: {
  rules: AlarmRule[];
  canChange: boolean;
  canDelete: boolean;
  pendingId: number | null;
  onToggle: (rule: AlarmRule) => void;
  onDelete: (rule: AlarmRule) => void;
}) {
  const [confirmingId, setConfirmingId] = useState<number | null>(null);

  return (
    <ul className="rule-list">
      {rules.map((rule) => {
        const visual = METRIC_VISUALS[rule.metric];
        const Icon = visual.icon;
        const busy = pendingId === rule.id;
        return (
          <li key={rule.id} className={`rule-row ${rule.enabled ? "is-enabled" : "is-disabled"}`} aria-busy={busy}>
            <div className="rule-row-icon" style={{ color: visual.color }}>
              <Icon size={18} aria-hidden="true" />
            </div>
            <div className="rule-row-main">
              <div className="rule-row-title">
                <strong>{rule.name}</strong>
                <span className={`badge ${rule.enabled ? "badge-on" : "badge-off"}`}>
                  {rule.enabled ? "Active" : "Inactive"}
                </span>
                {rule.active_alerts > 0 && (
                  <span className="badge badge-alarm">
                    En alarme · {rule.active_alerts} espace{rule.active_alerts > 1 ? "s" : ""}
                  </span>
                )}
              </div>
              <p className="rule-condition">
                {visual.label} <b>{rule.condition_label}</b> · {rule.zone_name ?? "Tous les espaces"}
              </p>
              <dl className="rule-facts">
                <div>
                  <dt>Gravité</dt>
                  <dd className={`severity-text severity-${rule.severity}`}>{SEVERITY_LABELS[rule.severity]}</dd>
                </div>
                <div>
                  <dt>Durée minimale</dt>
                  <dd>{formatDuration(rule.min_duration_seconds)}</dd>
                </div>
                <div>
                  <dt>Hystérésis</dt>
                  <dd>{rule.hysteresis ? `${rule.hysteresis} ${rule.unit}` : "aucune"}</dd>
                </div>
              </dl>
              {rule.description && <p className="rule-description">{rule.description}</p>}
            </div>
            {(canChange || canDelete) && (
              <div className="rule-row-actions">
                {canChange && (
                  <>
                    <button type="button" className="secondary-button" disabled={busy} onClick={() => onToggle(rule)}>
                      {rule.enabled ? (
                        <BellOff size={15} aria-hidden="true" />
                      ) : (
                        <BellRing size={15} aria-hidden="true" />
                      )}
                      {rule.enabled ? "Désactiver" : "Activer"}
                    </button>
                    <Link className="secondary-button" to={routePath("alarmRuleEdit", { ruleId: rule.id })}>
                      <Pencil size={15} aria-hidden="true" /> Modifier
                    </Link>
                  </>
                )}
                {canDelete &&
                  (confirmingId === rule.id ? (
                    <span className="confirm-delete" role="group" aria-label="Confirmer la suppression">
                      Supprimer ?
                      <button
                        type="button"
                        className="danger-button"
                        disabled={busy}
                        onClick={() => {
                          setConfirmingId(null);
                          onDelete(rule);
                        }}
                      >
                        Oui
                      </button>
                      <button type="button" className="secondary-button" onClick={() => setConfirmingId(null)}>
                        Non
                      </button>
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="secondary-button danger-text"
                      disabled={busy}
                      onClick={() => setConfirmingId(rule.id)}
                    >
                      <Trash2 size={15} aria-hidden="true" /> Supprimer
                    </button>
                  ))}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
