import { LOCALE } from "../constants/app";
import { METRIC_VISUALS } from "../constants/metrics";
import { ZONE_DISPLAY_NAMES, ZONE_TYPE_LABELS } from "../constants/zones";
import type { MetricType } from "../resources/observation";

export function formatValue(value: number, metric: MetricType): string {
  return new Intl.NumberFormat(LOCALE, { maximumFractionDigits: METRIC_VISUALS[metric].decimals }).format(value);
}

export function formatNumber(value: number, digits = 2): string {
  return new Intl.NumberFormat(LOCALE, { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
}

export function formatTime(value?: string | Date | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat(LOCALE, { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(
    new Date(value),
  );
}

/**
 * Moment d'une mesure : l'heure seule si c'est aujourd'hui, sinon la date
 * et l'heure (« 6 nov., 03 h 05 ») — une mesure ancienne ne doit pas
 * passer pour une mesure du jour.
 */
export function formatReadingTime(value?: string | Date | null, now: Date = new Date()): string {
  if (!value) return "—";
  const date = new Date(value);
  if (date.toDateString() === now.toDateString()) return formatTime(date);
  return new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(
    date,
  );
}

/**
 * Point de départ d'une absence de mesure, sans ambiguïté avec une durée :
 * « 00 h 55 aujourd’hui » ou « le 6 nov. à 03 h 05 ».
 */
export function formatSince(value: string | Date, now: Date = new Date()): string {
  const date = new Date(value);
  const time = new Intl.DateTimeFormat(LOCALE, { hour: "2-digit", minute: "2-digit" }).format(date);
  if (date.toDateString() === now.toDateString()) return `${time} aujourd’hui`;
  const day = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short" }).format(date);
  return `le ${day} à ${time}`;
}

export function formatLongDate(value: Date): string {
  return new Intl.DateTimeFormat(LOCALE, { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(
    value,
  );
}

export function formatDateTime(value: string | Date): string {
  return new Intl.DateTimeFormat(LOCALE, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

/** « 27 oct., 08:00 → 12:30 » ou « 20 oct., 08:00 → 27 oct., 12:30 ». */
export function formatRange(start: Date, end: Date): string {
  const sameDay = start.toDateString() === end.toDateString();
  const day = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short" });
  const time = new Intl.DateTimeFormat(LOCALE, { hour: "2-digit", minute: "2-digit" });
  return sameDay
    ? `${day.format(start)}, ${time.format(start)} → ${time.format(end)}`
    : `${day.format(start)}, ${time.format(start)} → ${day.format(end)}, ${time.format(end)}`;
}

/** Durée lisible : 0 → « immédiat », 90 → « 1 min 30 s », 7200 → « 2 h ». */
export function formatDuration(seconds: number): string {
  if (seconds <= 0) return "immédiat";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return [h && `${h} h`, m && `${m} min`, s && `${s} s`].filter(Boolean).join(" ");
}

/** Granularité d'agrégation : 15 → « 15 min », 60 → « 1 h », 1440 → « 1 jour ». */
export function formatBucket(minutes: number): string {
  if (minutes >= 1440) return `${minutes / 1440} jour${minutes > 1440 ? "s" : ""}`;
  if (minutes >= 60) return `${minutes / 60} h`;
  return `${minutes} min`;
}

export function formatZoneType(value: string): string {
  return ZONE_TYPE_LABELS[value] || value.replaceAll("_", " ");
}

export function zoneDisplayName(zone: { code: string; name: string } | undefined | null): string {
  if (!zone) return "—";
  return ZONE_DISPLAY_NAMES[zone.code] ?? ZONE_DISPLAY_NAMES[zone.name] ?? zone.name;
}

export function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

/** Origine lisible d'une alerte : règle, qualité des données ou règle supprimée. */
export function alertOrigin(alert: { rule: number | null; rule_name: string | null; code: string }): string {
  if (alert.rule_name) return alert.rule_name;
  if (alert.code.startsWith("DATA_QUALITY")) return "Qualité des données";
  if (alert.code.startsWith("RULE_")) return `Règle supprimée (n° ${alert.code.slice(5)})`;
  return alert.code;
}

/** Proportion (0–1) en pourcentage arrondi : « 42 % ». */
export function formatRatio(ratio: number | null | undefined): string {
  if (ratio == null) return "—";
  return `${Math.round(ratio * 100)} %`;
}
