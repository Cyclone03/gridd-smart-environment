import type { FieldErrors } from "../types/common";
import type { Severity } from "./alert";
import type { MetricType } from "./observation";

/**
 * Règles d'alarme configurables. Contrat : /api/alarm-rules/ (docs/api.md).
 * La validation ci-dessous donne un retour immédiat dans le formulaire ; le
 * backend applique les mêmes règles et reste l'autorité.
 */

export type AlarmOperator = "gt" | "gte" | "lt" | "lte" | "outside_range" | "inside_range";

export interface AlarmRule {
  id: number;
  name: string;
  description: string;
  /** Code de zone ; `null` = toutes les zones. */
  zone: string | null;
  zone_name: string | null;
  metric: MetricType;
  operator: AlarmOperator;
  threshold: number;
  threshold_high: number | null;
  unit: string;
  /** Condition lisible calculée par le backend, ex. « > 30 °C ». */
  condition_label: string;
  enabled: boolean;
  severity: Severity;
  min_duration_seconds: number;
  hysteresis: number;
  /** Nombre d'alertes actuellement actives pour cette règle. */
  active_alerts: number;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
}

export type AlarmRulePayload = Pick<
  AlarmRule,
  | "name"
  | "description"
  | "zone"
  | "metric"
  | "operator"
  | "threshold"
  | "threshold_high"
  | "enabled"
  | "severity"
  | "min_duration_seconds"
  | "hysteresis"
>;

export interface AlarmMetricMeta {
  key: MetricType;
  label: string;
  unit: string;
  /** Valeur de comptage : seuils entiers. */
  integer: boolean;
  min: number | null;
  max: number | null;
  operators: AlarmOperator[];
}

export interface AlarmOperatorMeta {
  key: AlarmOperator;
  label: string;
  symbol: string | null;
  range: boolean;
}

/** Catalogue renvoyé par GET /api/alarm-rules/metadata/. */
export interface AlarmMetadata {
  metrics: AlarmMetricMeta[];
  operators: AlarmOperatorMeta[];
  severities: { key: Severity; label: string }[];
  max_duration_seconds: number;
}

export type DurationUnit = "s" | "min";

/** Valeurs du formulaire, saisies sous forme de texte. */
export interface AlarmRuleDraft {
  name: string;
  description: string;
  /** Code de zone, ou "" pour toutes les zones. */
  zone: string;
  metric: MetricType | "";
  operator: AlarmOperator | "";
  threshold: string;
  threshold_high: string;
  enabled: boolean;
  severity: Severity;
  min_duration: string;
  min_duration_unit: DurationUnit;
  hysteresis: string;
}

export type AlarmRuleField = keyof AlarmRulePayload | "min_duration";

export function emptyAlarmRuleDraft(): AlarmRuleDraft {
  return {
    name: "",
    description: "",
    zone: "",
    metric: "",
    operator: "",
    threshold: "",
    threshold_high: "",
    enabled: true,
    severity: "warning",
    min_duration: "0",
    min_duration_unit: "min",
    hysteresis: "0",
  };
}

export function draftFromRule(rule: AlarmRule): AlarmRuleDraft {
  const inMinutes = rule.min_duration_seconds % 60 === 0;
  return {
    name: rule.name,
    description: rule.description,
    zone: rule.zone ?? "",
    metric: rule.metric,
    operator: rule.operator,
    threshold: String(rule.threshold),
    threshold_high: rule.threshold_high == null ? "" : String(rule.threshold_high),
    enabled: rule.enabled,
    severity: rule.severity,
    min_duration: String(inMinutes ? rule.min_duration_seconds / 60 : rule.min_duration_seconds),
    min_duration_unit: inMinutes ? "min" : "s",
    hysteresis: String(rule.hysteresis),
  };
}

/** Convertit « 21,5 » ou « 21.5 » en nombre ; `null` si invalide. */
export function parseDecimal(value: string): number | null {
  const normalized = value.trim().replace(/\s/g, "").replace(",", ".");
  if (!normalized || !/^-?\d+(\.\d+)?$/.test(normalized)) return null;
  return Number(normalized);
}

export function isRangeOperator(operator: string): boolean {
  return operator === "outside_range" || operator === "inside_range";
}

export function validateAlarmRuleDraft(
  draft: AlarmRuleDraft,
  metadata: AlarmMetadata,
): { payload: AlarmRulePayload | null; errors: FieldErrors<AlarmRuleField> } {
  const errors: FieldErrors<AlarmRuleField> = {};
  const metric = metadata.metrics.find((item) => item.key === draft.metric);
  const range = isRangeOperator(draft.operator);

  if (!draft.name.trim()) errors.name = "Le nom est obligatoire.";
  else if (draft.name.trim().length > 120) errors.name = "Le nom ne doit pas dépasser 120 caractères.";

  if (!metric) errors.metric = "Choisissez le paramètre surveillé.";
  if (!draft.operator) errors.operator = "Choisissez une condition.";
  else if (metric && !metric.operators.includes(draft.operator))
    errors.operator = "Cette condition n'est pas disponible pour ce paramètre.";

  const checkValue = (raw: string, field: "threshold" | "threshold_high"): number | null => {
    const value = parseDecimal(raw);
    if (value === null) {
      errors[field] = raw.trim() ? "Saisissez un nombre valide." : "Ce seuil est obligatoire.";
      return null;
    }
    if (metric?.integer && !Number.isInteger(value)) {
      errors[field] = "Ce paramètre est un comptage : utilisez un nombre entier.";
    } else if (metric && metric.min != null && metric.max != null && (value < metric.min || value > metric.max)) {
      errors[field] = `Valeur hors des limites du capteur (${metric.min} à ${metric.max} ${metric.unit}).`;
    }
    return value;
  };

  const threshold = checkValue(draft.threshold, "threshold");
  const thresholdHigh = range ? checkValue(draft.threshold_high, "threshold_high") : null;
  if (range && threshold !== null && thresholdHigh !== null && !errors.threshold_high && thresholdHigh <= threshold) {
    errors.threshold_high = "La borne haute doit être supérieure à la borne basse.";
  }

  const hysteresis = parseDecimal(draft.hysteresis || "0");
  if (hysteresis === null || hysteresis < 0) errors.hysteresis = "L'hystérésis doit être un nombre positif ou nul.";
  else if (metric?.integer && !Number.isInteger(hysteresis))
    errors.hysteresis = "Ce paramètre est un comptage : utilisez un nombre entier.";
  else if (
    draft.operator === "outside_range" &&
    threshold !== null &&
    thresholdHigh !== null &&
    thresholdHigh > threshold &&
    2 * hysteresis >= thresholdHigh - threshold
  )
    errors.hysteresis = "L'hystérésis doit être inférieure à la moitié de l'intervalle.";

  const durationValue = parseDecimal(draft.min_duration || "0");
  const minDurationSeconds =
    durationValue === null ? null : Math.round(durationValue * (draft.min_duration_unit === "min" ? 60 : 1));
  if (minDurationSeconds === null || minDurationSeconds < 0)
    errors.min_duration = "La durée minimale doit être un nombre positif ou nul.";
  else if (minDurationSeconds > metadata.max_duration_seconds)
    errors.min_duration = `La durée minimale ne peut pas dépasser ${metadata.max_duration_seconds / 3600} h.`;

  if (!metadata.severities.some((item) => item.key === draft.severity)) errors.severity = "Gravité inconnue.";

  if (Object.keys(errors).length) return { payload: null, errors };

  return {
    payload: {
      name: draft.name.trim(),
      description: draft.description.trim(),
      zone: draft.zone || null,
      metric: metric!.key,
      operator: draft.operator as AlarmOperator,
      threshold: threshold!,
      threshold_high: range ? thresholdHigh : null,
      enabled: draft.enabled,
      severity: draft.severity,
      min_duration_seconds: minDurationSeconds!,
      hysteresis: hysteresis!,
    },
    errors,
  };
}
