import { CalendarClock, Check, RefreshCw } from "lucide-react";
import { useEffect, useId, useState, type FormEvent } from "react";
import { MAX_RANGE_DAYS, PERIOD_PRESETS } from "../../constants/periods";
import {
  validateCustomRange,
  type ObservationPeriod,
  type PeriodPresetKey,
  type ResolvedPeriod,
} from "../../resources/period";
import type { FieldErrors } from "../../types/common";
import { toDateTimeLocalValue } from "../../utils/dates";
import { formatRange } from "../../utils/format";
import { samePeriod } from "../../utils/period";

type Selection = PeriodPresetKey | "custom";

function draftFrom(period: ObservationPeriod, resolved: ResolvedPeriod) {
  return {
    selection: (period.kind === "preset" ? period.preset : "custom") as Selection,
    start: toDateTimeLocalValue(resolved.start),
    end: toDateTimeLocalValue(resolved.end),
  };
}

/**
 * Sélecteur de période d'observation.
 *
 * L'utilisateur choisit une période prédéfinie ou une plage personnalisée,
 * puis l'applique avec « Appliquer ». La période réellement affichée reste
 * visible en permanence, ainsi que l'indication de modifications en attente.
 */
export function PeriodSelector({
  period,
  resolved,
  onApply,
  onRefresh,
  busy = false,
  maxRangeDays = MAX_RANGE_DAYS,
}: {
  period: ObservationPeriod;
  resolved: ResolvedPeriod;
  onApply: (period: ObservationPeriod) => void;
  onRefresh?: () => void;
  busy?: boolean;
  maxRangeDays?: number;
}) {
  const id = useId();
  const [draft, setDraft] = useState(() => draftFrom(period, resolved));
  const [errors, setErrors] = useState<FieldErrors<"start" | "end">>({});

  // Une période appliquée ailleurs (URL, navigation) réinitialise le brouillon.
  const appliedKey = period.kind === "preset" ? period.preset : `${period.start}|${period.end}`;
  useEffect(() => {
    setDraft(draftFrom(period, resolved));
    setErrors({});
  }, [appliedKey]);

  const draftPeriod: ObservationPeriod | null =
    draft.selection === "custom" ? null : { kind: "preset", preset: draft.selection };
  const pending =
    draft.selection === "custom"
      ? period.kind !== "custom" ||
        draft.start !== toDateTimeLocalValue(resolved.start) ||
        draft.end !== toDateTimeLocalValue(resolved.end)
      : !samePeriod(draftPeriod!, period);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (draft.selection !== "custom") {
      setErrors({});
      onApply({ kind: "preset", preset: draft.selection });
      return;
    }
    const result = validateCustomRange(draft.start, draft.end, { maxRangeDays });
    setErrors(result.errors);
    if (result.start && result.end)
      onApply({ kind: "custom", start: result.start.toISOString(), end: result.end.toISOString() });
  };

  return (
    <form className="period-selector" onSubmit={submit} aria-label="Période d’observation" noValidate>
      <div className="period-fields">
        <div className="field">
          <label htmlFor={`${id}-preset`}>Période</label>
          <select
            id={`${id}-preset`}
            value={draft.selection}
            onChange={(event) => setDraft((current) => ({ ...current, selection: event.target.value as Selection }))}
          >
            {PERIOD_PRESETS.map((preset) => (
              <option key={preset.key} value={preset.key}>
                {preset.label}
              </option>
            ))}
            <option value="custom">Période personnalisée…</option>
          </select>
        </div>
        {draft.selection === "custom" && (
          <>
            <div className="field">
              <label htmlFor={`${id}-start-input`}>Début</label>
              <input
                id={`${id}-start-input`}
                type="datetime-local"
                value={draft.start}
                max={toDateTimeLocalValue(new Date())}
                aria-invalid={Boolean(errors.start)}
                aria-describedby={errors.start ? `${id}-start` : undefined}
                onChange={(event) => setDraft((current) => ({ ...current, start: event.target.value }))}
              />
              {errors.start && (
                <em className="field-error" id={`${id}-start`}>
                  {errors.start}
                </em>
              )}
            </div>
            <div className="field">
              <label htmlFor={`${id}-end-input`}>Fin</label>
              <input
                id={`${id}-end-input`}
                type="datetime-local"
                value={draft.end}
                aria-invalid={Boolean(errors.end)}
                aria-describedby={errors.end ? `${id}-end` : undefined}
                onChange={(event) => setDraft((current) => ({ ...current, end: event.target.value }))}
              />
              {errors.end && (
                <em className="field-error" id={`${id}-end`}>
                  {errors.end}
                </em>
              )}
            </div>
          </>
        )}
        <div className="period-actions">
          <button type="submit" className="primary-button" disabled={busy && !pending}>
            <Check size={15} aria-hidden="true" /> Appliquer
          </button>
          {onRefresh && (
            <button type="button" className="secondary-button" onClick={onRefresh} disabled={busy} title="Actualiser">
              <RefreshCw size={15} className={busy ? "spin" : undefined} aria-hidden="true" />
              <span className="sr-only">Actualiser les données</span>
            </button>
          )}
        </div>
      </div>
      <p className="period-applied" aria-live="polite">
        <CalendarClock size={14} aria-hidden="true" />
        <span>
          Période affichée : <strong>{resolved.label}</strong>
          {period.kind === "preset" && <> · {formatRange(resolved.start, resolved.end)}</>}
          {resolved.live && " · actualisation automatique"}
        </span>
        {pending && <em className="period-pending">Modification non appliquée</em>}
      </p>
    </form>
  );
}
