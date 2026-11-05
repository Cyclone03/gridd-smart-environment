import { Save, X } from "lucide-react";
import { useId, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { SEVERITY_LABELS } from "../../constants/alerts";
import {
  isRangeOperator,
  parseDecimal,
  validateAlarmRuleDraft,
  type AlarmMetadata,
  type AlarmRuleDraft,
  type AlarmRuleField,
  type AlarmRulePayload,
} from "../../resources/alarmRule";
import type { Zone } from "../../resources/zone";
import type { FieldErrors } from "../../types/common";
import { formatDuration, zoneDisplayName } from "../../utils/format";
import { ErrorMessage } from "../common/Feedback";

/**
 * Formulaire de création / modification d'une règle d'alarme.
 *
 * Validation immédiate côté interface (resources/alarmRule.ts), puis
 * affichage des erreurs renvoyées par l'API (`serverErrors`) sur les champs.
 */
export function AlarmRuleForm({
  initial,
  metadata,
  zones,
  submitting,
  serverMessage,
  serverErrors = {},
  submitLabel,
  onSubmit,
  onCancel,
}: {
  initial: AlarmRuleDraft;
  metadata: AlarmMetadata;
  zones: Zone[];
  submitting: boolean;
  serverMessage?: string | null;
  serverErrors?: Record<string, string>;
  submitLabel: string;
  onSubmit: (payload: AlarmRulePayload) => void;
  onCancel: () => void;
}) {
  const id = useId();
  const [draft, setDraft] = useState<AlarmRuleDraft>(initial);
  const [errors, setErrors] = useState<FieldErrors<AlarmRuleField>>({});
  const [submitted, setSubmitted] = useState(false);

  const metric = metadata.metrics.find((item) => item.key === draft.metric);
  const operators = metadata.operators.filter((op) => !metric || metric.operators.includes(op.key));
  const range = isRangeOperator(draft.operator);
  const unit = metric?.unit ?? "";

  const update = <K extends keyof AlarmRuleDraft>(field: K, value: AlarmRuleDraft[K]) => {
    const next = { ...draft, [field]: value };
    if (field === "metric") {
      // Une condition non disponible pour le nouveau paramètre est réinitialisée.
      const meta = metadata.metrics.find((item) => item.key === value);
      if (meta && next.operator && !meta.operators.includes(next.operator)) next.operator = "";
    }
    setDraft(next);
    if (submitted) setErrors(validateAlarmRuleDraft(next, metadata).errors);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    const result = validateAlarmRuleDraft(draft, metadata);
    setErrors(result.errors);
    if (result.payload) onSubmit(result.payload);
  };

  const errorFor = (field: AlarmRuleField) => errors[field] ?? serverErrors[field];
  const describedBy = (field: AlarmRuleField) => (errorFor(field) ? `${id}-${field}-error` : undefined);
  const fieldError = (field: AlarmRuleField) =>
    errorFor(field) ? (
      <em className="field-error" id={`${id}-${field}-error`}>
        {errorFor(field)}
      </em>
    ) : null;

  const summary = useMemo(() => describeDraft(draft, metadata, zones), [draft, metadata, zones]);
  const generalServerErrors = [
    serverErrors.non_field_errors,
    serverErrors.zone && !errors.zone ? serverErrors.zone : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <form className="rule-form" onSubmit={submit} noValidate aria-label="Règle d’alarme">
      {serverMessage && <ErrorMessage>{[serverMessage, generalServerErrors].filter(Boolean).join(" ")}</ErrorMessage>}

      <fieldset>
        <legend>Identification</legend>
        <Field controlId={`${id}-name`} label="Nom de la règle" required error={fieldError("name")}>
          <input
            id={`${id}-name`}
            value={draft.name}
            maxLength={120}
            onChange={(event) => update("name", event.target.value)}
            aria-invalid={Boolean(errorFor("name"))}
            aria-describedby={describedBy("name")}
          />
        </Field>
        <Field controlId={`${id}-description`} label="Description (facultative)">
          <textarea
            id={`${id}-description`}
            rows={2}
            value={draft.description}
            onChange={(event) => update("description", event.target.value)}
          />
        </Field>
      </fieldset>

      <fieldset>
        <legend>Condition de déclenchement</legend>
        <div className="form-grid">
          <Field controlId={`${id}-metric`} label="Paramètre surveillé" required error={fieldError("metric")}>
            <select
              id={`${id}-metric`}
              value={draft.metric}
              onChange={(event) => update("metric", event.target.value as AlarmRuleDraft["metric"])}
              aria-invalid={Boolean(errorFor("metric"))}
              aria-describedby={describedBy("metric")}
            >
              <option value="">Choisir…</option>
              {metadata.metrics.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label} ({item.unit})
                </option>
              ))}
            </select>
          </Field>
          <Field controlId={`${id}-zone`} label="Espace" error={fieldError("zone")}>
            <select id={`${id}-zone`} value={draft.zone} onChange={(event) => update("zone", event.target.value)}>
              <option value="">Tous les espaces</option>
              {zones.map((zone) => (
                <option key={zone.code} value={zone.code}>
                  {zoneDisplayName(zone)}
                </option>
              ))}
            </select>
          </Field>
          <Field controlId={`${id}-operator`} label="Condition" required error={fieldError("operator")}>
            <select
              id={`${id}-operator`}
              value={draft.operator}
              onChange={(event) => update("operator", event.target.value as AlarmRuleDraft["operator"])}
              aria-invalid={Boolean(errorFor("operator"))}
              aria-describedby={describedBy("operator")}
            >
              <option value="">Choisir…</option>
              {operators.map((op) => (
                <option key={op.key} value={op.key}>
                  {op.label}
                  {op.symbol ? ` (${op.symbol})` : ""}
                </option>
              ))}
            </select>
          </Field>
          <Field
            controlId={`${id}-threshold`}
            label={range ? "Borne basse" : "Seuil"}
            required
            error={fieldError("threshold")}
            suffix={unit}
          >
            <input
              id={`${id}-threshold`}
              inputMode="decimal"
              value={draft.threshold}
              onChange={(event) => update("threshold", event.target.value)}
              aria-invalid={Boolean(errorFor("threshold"))}
              aria-describedby={describedBy("threshold")}
            />
          </Field>
          {range && (
            <Field
              controlId={`${id}-threshold_high`}
              label="Borne haute"
              required
              error={fieldError("threshold_high")}
              suffix={unit}
            >
              <input
                id={`${id}-threshold_high`}
                inputMode="decimal"
                value={draft.threshold_high}
                onChange={(event) => update("threshold_high", event.target.value)}
                aria-invalid={Boolean(errorFor("threshold_high"))}
                aria-describedby={describedBy("threshold_high")}
              />
            </Field>
          )}
        </div>
        {metric?.integer && <p className="form-hint">Le nombre de personnes est un comptage : seuils entiers.</p>}
      </fieldset>

      <fieldset>
        <legend>Comportement</legend>
        <div className="form-grid">
          <Field controlId={`${id}-severity`} label="Gravité" required error={fieldError("severity")}>
            <select
              id={`${id}-severity`}
              value={draft.severity}
              onChange={(event) => update("severity", event.target.value as AlarmRuleDraft["severity"])}
            >
              {metadata.severities.map((item) => (
                <option key={item.key} value={item.key}>
                  {SEVERITY_LABELS[item.key] ?? item.label}
                </option>
              ))}
            </select>
          </Field>
          <Field
            controlId={`${id}-min_duration`}
            label="Durée minimale de dépassement"
            error={fieldError("min_duration") ?? fieldError("min_duration_seconds")}
            hint="0 = déclenchement immédiat."
          >
            <div className="input-group">
              <input
                id={`${id}-min_duration`}
                inputMode="decimal"
                value={draft.min_duration}
                onChange={(event) => update("min_duration", event.target.value)}
                aria-invalid={Boolean(errorFor("min_duration"))}
              />
              <select
                value={draft.min_duration_unit}
                onChange={(event) =>
                  update("min_duration_unit", event.target.value as AlarmRuleDraft["min_duration_unit"])
                }
                aria-label="Unité de durée"
              >
                <option value="s">secondes</option>
                <option value="min">minutes</option>
              </select>
            </div>
          </Field>
          <Field
            controlId={`${id}-hysteresis`}
            label="Hystérésis (retour à la normale)"
            error={fieldError("hysteresis")}
            suffix={unit}
            hint="Marge à franchir dans l’autre sens avant de résoudre l’alarme."
          >
            <input
              id={`${id}-hysteresis`}
              inputMode="decimal"
              value={draft.hysteresis}
              onChange={(event) => update("hysteresis", event.target.value)}
              aria-invalid={Boolean(errorFor("hysteresis"))}
              aria-describedby={describedBy("hysteresis")}
            />
          </Field>
          <label className="toggle-field">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(event) => update("enabled", event.target.checked)}
            />
            <span>Règle active</span>
          </label>
        </div>
      </fieldset>

      <div className="rule-summary" aria-live="polite">
        <strong>Comportement attendu</strong>
        <p>{summary}</p>
      </div>

      <div className="form-actions">
        <button type="button" className="secondary-button" onClick={onCancel} disabled={submitting}>
          <X size={15} aria-hidden="true" /> Annuler
        </button>
        <button type="submit" className="primary-button" disabled={submitting}>
          <Save size={15} aria-hidden="true" /> {submitting ? "Enregistrement…" : submitLabel}
        </button>
      </div>
    </form>
  );
}

function Field({
  controlId,
  label,
  required,
  error,
  hint,
  suffix,
  children,
}: {
  controlId: string;
  label: string;
  required?: boolean;
  error?: ReactNode;
  hint?: string;
  suffix?: string;
  children: ReactNode;
}) {
  return (
    <div className="field">
      <label htmlFor={controlId}>
        {label}
        {required && <b aria-hidden="true"> *</b>}
      </label>
      {suffix ? (
        <div className="input-suffix">
          {children}
          <i>{suffix}</i>
        </div>
      ) : (
        children
      )}
      {hint && !error && <small>{hint}</small>}
      {error}
    </div>
  );
}

/** Phrase récapitulant la règle en cours de saisie. */
export function describeDraft(draft: AlarmRuleDraft, metadata: AlarmMetadata, zones: Zone[]): string {
  const metric = metadata.metrics.find((item) => item.key === draft.metric);
  const operator = metadata.operators.find((item) => item.key === draft.operator);
  if (!metric || !operator) return "Choisissez un paramètre et une condition pour voir le comportement de la règle.";
  const low = draft.threshold || "…";
  const high = draft.threshold_high || "…";
  const condition = operator.range
    ? `${operator.key === "outside_range" ? "sort de" : "entre dans"} l’intervalle [${low} ; ${high}] ${metric.unit}`
    : `${operator.symbol ?? operator.label} ${low} ${metric.unit}`;
  const zone = zones.find((item) => item.code === draft.zone);
  const where = zone ? `dans « ${zoneDisplayName(zone)} »` : "dans n’importe quel espace";
  const durationValue = parseDecimal(draft.min_duration || "0") ?? 0;
  const seconds = Math.round(durationValue * (draft.min_duration_unit === "min" ? 60 : 1));
  const duration = seconds > 0 ? ` pendant au moins ${formatDuration(seconds)}` : "";
  const hysteresis = parseDecimal(draft.hysteresis || "0") ?? 0;
  const recovery =
    hysteresis > 0
      ? ` Elle sera résolue lorsque la valeur reviendra d’au moins ${draft.hysteresis} ${metric.unit} dans la zone normale.`
      : " Elle sera résolue dès que la condition ne sera plus remplie.";
  const state = draft.enabled ? "" : " (règle inactive : aucune alarme ne sera déclenchée)";
  return `Une alarme « ${SEVERITY_LABELS[draft.severity].toLowerCase()} » sera déclenchée lorsque la mesure « ${metric.label} » ${operator.range ? "" : "sera "}${condition} ${where}${duration}.${recovery}${state}`;
}
