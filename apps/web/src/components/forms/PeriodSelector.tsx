import { CalendarClock, RefreshCw } from "lucide-react";
import { useEffect, useId, useState } from "react";
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
 * Les périodes prédéfinies sont appliquées immédiatement.
 * Les périodes personnalisées sont validées et appliquées
 * automatiquement lorsque les deux dates sont valides.
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
  const appliedKey =
    period.kind === "preset"
      ? period.preset
      : `${period.start}|${period.end}`;

  useEffect(() => {
    setDraft(draftFrom(period, resolved));
    setErrors({});
  }, [appliedKey]);

  /**
   * Applique immédiatement une période prédéfinie.
   */
  const handlePresetChange = (selection: Selection) => {
    setDraft((current) => ({
      ...current,
      selection,
    }));

    setErrors({});

    if (selection !== "custom") {
      onApply({
        kind: "preset",
        preset: selection,
      });
    }
  };

  /**
   * Valide et applique automatiquement une période personnalisée.
   */
  const handleCustomChange = (
    field: "start" | "end",
    value: string,
  ) => {
    const nextDraft = {
      ...draft,
      [field]: value,
    };

    setDraft(nextDraft);

    const result = validateCustomRange(
      nextDraft.start,
      nextDraft.end,
      { maxRangeDays },
    );

    setErrors(result.errors);

    if (result.start && result.end) {
      onApply({
        kind: "custom",
        start: result.start.toISOString(),
        end: result.end.toISOString(),
      });
    }
  };

  return (
    <form
      className="period-selector"
      aria-label="Période d’observation"
      noValidate
      onSubmit={(event) => event.preventDefault()}
    >
      <div className="period-fields">
        <div className="field">
          <label htmlFor={`${id}-preset`}>Période</label>

          <select
            id={`${id}-preset`}
            value={draft.selection}
            disabled={busy}
            onChange={(event) =>
              handlePresetChange(event.target.value as Selection)
            }
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
                disabled={busy}
                aria-invalid={Boolean(errors.start)}
                aria-describedby={
                  errors.start ? `${id}-start` : undefined
                }
                onChange={(event) =>
                  handleCustomChange("start", event.target.value)
                }
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
                disabled={busy}
                aria-invalid={Boolean(errors.end)}
                aria-describedby={
                  errors.end ? `${id}-end` : undefined
                }
                onChange={(event) =>
                  handleCustomChange("end", event.target.value)
                }
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
          {onRefresh && (
            <button
              type="button"
              className="primary-button"
              onClick={onRefresh}
              disabled={busy}
              title="Actualiser"
            >
              <RefreshCw
                size={15}
                className={busy ? "spin" : ""}
                aria-hidden="true"
              />
              <span className="sr-only">
                Actualiser les données
              </span>
            </button>
          )}
        </div>
      </div>

      <p className="period-applied" aria-live="polite">
        <CalendarClock size={14} aria-hidden="true" />

        <span>
          Période affichée : <strong>{resolved.label}</strong>

          {period.kind === "preset" && (
            <> · {formatRange(resolved.start, resolved.end)}</>
          )}

          {resolved.live && " · actualisation automatique"}
        </span>
      </p>
    </form>
  );
}
