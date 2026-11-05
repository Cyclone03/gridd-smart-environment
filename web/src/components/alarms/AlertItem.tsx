import { AlertTriangle, Check, ChevronDown, Eye } from "lucide-react";
import { SEVERITY_LABELS } from "../../constants/alerts";
import type { Alert } from "../../resources/alert";
import { alertOrigin, formatDateTime, formatNumber } from "../../utils/format";

/** Alerte active dépliable ; l'ouvrir la marque comme consultée. */
export function AlertItem({
  alert,
  read,
  open,
  onToggle,
  onShowRules,
}: {
  alert: Alert;
  read: boolean;
  open: boolean;
  onToggle: () => void;
  onShowRules: () => void;
}) {
  return (
    <article
      className={`alert-item severity-${alert.severity} ${read ? "is-read" : "is-unread"} ${open ? "is-open" : ""}`}
    >
      <button type="button" className="alert-trigger" aria-expanded={open} onClick={onToggle}>
        <span className="alert-icon">
          <AlertTriangle size={19} aria-hidden="true" />
        </span>
        <span className="alert-copy">
          <span className="alert-title">
            <strong>{alert.zone_name}</strong>
            {read ? (
              <em>
                <Check size={12} /> Consultée
              </em>
            ) : (
              <em className="new-alert">
                <Eye size={12} /> Nouvelle
              </em>
            )}
          </span>
          <span>{alert.message}</span>
          <small>{formatDateTime(alert.created_at)}</small>
        </span>
        <ChevronDown className="alert-chevron" size={18} aria-hidden="true" />
      </button>
      {open && (
        <div className="alert-details">
          <div>
            <span>Niveau</span>
            <strong>{SEVERITY_LABELS[alert.severity]}</strong>
          </div>
          <div>
            <span>{alert.rule ? "Règle déclenchée" : "Origine"}</span>
            <strong>{alertOrigin(alert)}</strong>
          </div>
          <div>
            <span>Valeur au déclenchement</span>
            <strong>{alert.trigger_value == null ? "—" : formatNumber(alert.trigger_value, 1)}</strong>
          </div>
          <button type="button" onClick={onShowRules}>
            Voir les règles de cet espace
          </button>
        </div>
      )}
    </article>
  );
}
