import type { AlertResolution, Severity } from "../resources/alert";

export const SEVERITY_LABELS: Record<Severity, string> = {
  info: "Information",
  warning: "Avertissement",
  critical: "Critique",
};

export const RESOLUTION_LABELS: Record<AlertResolution, string> = {
  "": "—",
  returned_to_normal: "Retour à la normale",
  rule_disabled: "Règle désactivée",
  rule_updated: "Règle modifiée",
  rule_deleted: "Règle supprimée",
  migrated: "Remplacée par les règles configurables",
};

/** Profondeur de l'historique des déclenchements affiché sur la page Alertes. */
export const ALERT_HISTORY_DAYS = 7;
export const ALERT_HISTORY_LIMIT = 50;
