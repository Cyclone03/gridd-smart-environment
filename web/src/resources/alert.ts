/**
 * Alertes et événements d'alarme. Une alerte est un épisode : déclenchement
 * (`created_at`, `trigger_value`) puis éventuel retour à la normale
 * (`resolved_at`, `resolution`). Contrat : GET /api/alerts/.
 */

export type Severity = "info" | "warning" | "critical";

export type AlertResolution =
  | ""
  | "returned_to_normal"
  | "rule_disabled"
  | "rule_updated"
  | "rule_deleted"
  | "migrated";

export interface Alert {
  id: number;
  zone: number;
  zone_code: string;
  zone_name: string;
  observation: number | null;
  /** Règle à l'origine de l'alerte ; `null` pour la qualité des données. */
  rule: number | null;
  rule_name: string | null;
  code: string;
  message: string;
  severity: Severity;
  trigger_value: number | null;
  created_at: string;
  resolved_at: string | null;
  resolution: AlertResolution;
  active: boolean;
}

export interface AlertFilters {
  active?: boolean;
  zone?: string;
  rule?: number;
  severity?: Severity;
  since?: Date;
  until?: Date;
  limit?: number;
}
