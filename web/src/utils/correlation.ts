/**
 * Statistiques de corrélation entre mesures d'un même espace.
 *
 * Les séries sont les moyennes par créneau renvoyées par l'historique. Deux
 * mesures sont comparées sur leurs créneaux communs (coefficient de Pearson),
 * avec recherche d'un éventuel décalage temporel et corrélation partielle pour
 * repérer les liens indirects.
 */
import { CORRELATION_METRICS, METRIC_UNITS, type CorrelationMetric } from "../constants/metrics";
import type { ZoneHistory } from "../resources/history";

/** Nombre minimal de créneaux communs pour calculer une corrélation. */
export const MIN_POINTS = 8;
/** Décalage maximal testé (en nombre de créneaux) pour détecter un effet retardé. */
export const MAX_LAG = 4;

export interface Series {
  type: CorrelationMetric;
  unit: string;
  bucketMinutes: number;
  values: Map<number, number>;
  times: Map<number, string>;
}

export interface PairResult {
  a: CorrelationMetric;
  b: CorrelationMetric;
  n: number;
  r: number | null;
  pValue: number | null;
  slope: number | null;
  intercept: number | null;
  points: { x: number; y: number; time: string }[];
  bestLag: { lag: number; r: number } | null;
  /** Corrélation partielle en neutralisant la troisième mesure (si disponible). */
  partial: { control: CorrelationMetric; r: number } | null;
}

export function pearson(xs: number[], ys: number[]) {
  const n = xs.length;
  if (n < 3) return null;
  const mx = xs.reduce((s, v) => s + v, 0) / n;
  const my = ys.reduce((s, v) => s + v, 0) / n;
  let sxy = 0;
  let sxx = 0;
  let syy = 0;
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - mx;
    const dy = ys[i] - my;
    sxy += dx * dy;
    sxx += dx * dx;
    syy += dy * dy;
  }
  if (sxx === 0 || syy === 0) return null; // une des séries est constante
  const r = sxy / Math.sqrt(sxx * syy);
  const slope = sxy / sxx;
  return { r: Math.max(-1, Math.min(1, r)), slope, intercept: my - slope * mx };
}

/** Fonction d'erreur (approximation d'Abramowitz & Stegun 7.1.26). */
function erf(x: number) {
  const sign = Math.sign(x);
  const t = 1 / (1 + 0.3275911 * Math.abs(x));
  const y =
    1 -
    ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x);
  return sign * y;
}

/** Valeur p bilatérale via la transformation de Fisher (approximation). */
export function pValueFor(r: number, n: number) {
  if (n < 4) return null;
  const clamped = Math.max(-0.999999, Math.min(0.999999, r));
  const z = Math.abs(Math.atanh(clamped)) * Math.sqrt(n - 3);
  return Math.max(0, 1 - erf(z / Math.SQRT2));
}

export function toSeries(history: ZoneHistory, type: CorrelationMetric): Series {
  const bucketMinutes = history.bucket_minutes || 15;
  const bucketMs = bucketMinutes * 60_000;
  const values = new Map<number, number>();
  const times = new Map<number, string>();
  for (const point of history.points) {
    const ts = Date.parse(point.time);
    if (!Number.isFinite(ts) || point.average == null || !Number.isFinite(point.average) || point.count === 0) continue;
    const key = Math.round(ts / bucketMs);
    values.set(key, point.average);
    times.set(key, point.time);
  }
  return { type, unit: history.unit || METRIC_UNITS[type], bucketMinutes, values, times };
}

function pairValues(a: Series, b: Series, lag = 0) {
  const xs: number[] = [];
  const ys: number[] = [];
  const keys: number[] = [];
  a.values.forEach((x, key) => {
    const y = b.values.get(key + lag);
    if (y != null) {
      xs.push(x);
      ys.push(y);
      keys.push(key);
    }
  });
  return { xs, ys, keys };
}

export function analysePair(a: Series, b: Series): PairResult {
  const { xs, ys, keys } = pairValues(a, b);
  const fit = xs.length >= MIN_POINTS ? pearson(xs, ys) : null;
  let bestLag: PairResult["bestLag"] = null;
  if (fit) {
    for (let lag = -MAX_LAG; lag <= MAX_LAG; lag++) {
      if (lag === 0) continue;
      const shifted = pairValues(a, b, lag);
      if (shifted.xs.length < MIN_POINTS) continue;
      const res = pearson(shifted.xs, shifted.ys);
      if (res && (!bestLag || Math.abs(res.r) > Math.abs(bestLag.r))) bestLag = { lag, r: res.r };
    }
    // On ne garde le décalage que s'il améliore nettement la relation.
    if (bestLag && Math.abs(bestLag.r) - Math.abs(fit.r) < 0.1) bestLag = null;
  }
  return {
    a: a.type,
    b: b.type,
    n: xs.length,
    r: fit?.r ?? null,
    pValue: fit ? pValueFor(fit.r, xs.length) : null,
    slope: fit?.slope ?? null,
    intercept: fit?.intercept ?? null,
    points: xs.map((x, i) => ({ x, y: ys[i], time: a.times.get(keys[i]) || "" })),
    bestLag,
    partial: null,
  };
}

/** Ajoute la corrélation partielle r(a,b | c) pour détecter les liens indirects. */
export function withPartials(pairs: PairResult[]): PairResult[] {
  const r = (x: CorrelationMetric, y: CorrelationMetric) =>
    pairs.find((p) => (p.a === x && p.b === y) || (p.a === y && p.b === x))?.r ?? null;
  return pairs.map((pair) => {
    const control = CORRELATION_METRICS.find((m) => m !== pair.a && m !== pair.b);
    if (!control || pair.r == null) return pair;
    const rac = r(pair.a, control);
    const rbc = r(pair.b, control);
    if (rac == null || rbc == null) return pair;
    const denom = Math.sqrt((1 - rac * rac) * (1 - rbc * rbc));
    if (denom < 1e-6) return pair;
    return { ...pair, partial: { control, r: Math.max(-1, Math.min(1, (pair.r - rac * rbc) / denom)) } };
  });
}

/** Analyse toutes les paires de séries disponibles. */
export function analyseAllPairs(series: Series[]): PairResult[] {
  const list: PairResult[] = [];
  for (let i = 0; i < series.length; i++)
    for (let j = i + 1; j < series.length; j++) list.push(analysePair(series[i], series[j]));
  return withPartials(list);
}

export function strengthOf(r: number) {
  const v = Math.abs(r);
  if (v < 0.2) return { label: "Très faible", level: 0 };
  if (v < 0.4) return { label: "Faible", level: 1 };
  if (v < 0.6) return { label: "Modérée", level: 2 };
  if (v < 0.8) return { label: "Forte", level: 3 };
  return { label: "Très forte", level: 4 };
}

export function isMeaningful(pair: PairResult) {
  return pair.r != null && Math.abs(pair.r) >= 0.4 && (pair.pValue ?? 1) < 0.05;
}

/** Lien apparent qui disparaît quand on neutralise la troisième mesure. */
export function isIndirect(pair: PairResult) {
  return isMeaningful(pair) && pair.partial != null && Math.abs(pair.partial.r) < 0.3;
}

export function pairKey(a: CorrelationMetric, b: CorrelationMetric) {
  return `${a}|${b}`;
}

/** Échelle divergente : bleu (négatif) ↔ orange brûlé (positif), plus foncé quand |r| est grand. */
export function correlationColor(r: number | null) {
  if (r == null) return "#8a9692";
  const v = Math.min(1, Math.abs(r));
  const light = 72 - v * 34;
  return r < 0 ? `hsl(200 62% ${light}%)` : `hsl(14 62% ${light}%)`;
}
