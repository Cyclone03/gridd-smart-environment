import { findPreset, PERIOD_PRESETS } from "../constants/periods";
import type { ObservationPeriod, PeriodPresetKey, ResolvedPeriod } from "../resources/period";
import { formatRange } from "./format";

/** Calcule les bornes effectives d'une période à l'instant `now`. */
export function resolvePeriod(period: ObservationPeriod, now: Date = new Date()): ResolvedPeriod {
  if (period.kind === "preset") {
    const preset = findPreset(period.preset) ?? PERIOD_PRESETS[0];
    const { start, end } = preset.resolve(now);
    return { start, end, label: preset.label, live: preset.live };
  }
  const start = new Date(period.start);
  const end = new Date(period.end);
  return { start, end, label: formatRange(start, end), live: false };
}

export function samePeriod(a: ObservationPeriod, b: ObservationPeriod): boolean {
  if (a.kind === "preset" && b.kind === "preset") return a.preset === b.preset;
  if (a.kind === "custom" && b.kind === "custom") return a.start === b.start && a.end === b.end;
  return false;
}

/** Représentation dans l'URL : `?period=24h` ou `?start=…&end=…`. */
export function periodToSearchParams(period: ObservationPeriod, params: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(params);
  next.delete("period");
  next.delete("start");
  next.delete("end");
  if (period.kind === "preset") next.set("period", period.preset);
  else {
    next.set("start", period.start);
    next.set("end", period.end);
  }
  return next;
}

export function periodFromSearchParams(params: URLSearchParams, fallback: ObservationPeriod): ObservationPeriod {
  const preset = params.get("period");
  if (preset && findPreset(preset)) return { kind: "preset", preset: preset as PeriodPresetKey };
  const start = params.get("start");
  const end = params.get("end");
  if (
    start &&
    end &&
    !Number.isNaN(Date.parse(start)) &&
    !Number.isNaN(Date.parse(end)) &&
    Date.parse(end) > Date.parse(start)
  )
    return { kind: "custom", start, end };
  // Compatibilité avec les anciens liens `?date=AAAA-MM-JJ`.
  const date = params.get("date");
  if (date && /^\d{4}-\d{2}-\d{2}$/.test(date)) {
    const dayStart = new Date(`${date}T00:00:00`);
    const dayEnd = new Date(dayStart);
    dayEnd.setDate(dayEnd.getDate() + 1);
    if (!Number.isNaN(dayStart.getTime()))
      return { kind: "custom", start: dayStart.toISOString(), end: dayEnd.toISOString() };
  }
  return fallback;
}
