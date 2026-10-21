import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ArrowRightLeft, Droplets, GitCompareArrows, Info, Lightbulb, Thermometer, Volume2 } from "lucide-react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { loadZoneDayHistory, loadZoneHistory } from "./api";
import type { MetricType, ZoneHistory } from "./types";

/* ------------------------------------------------------------------ */
/* Configuration                                                       */
/* ------------------------------------------------------------------ */

type EnvMetric = Extract<MetricType, "temperature" | "humidity" | "sound_level">;
type Period = "day" | "week";

const ENV_METRICS: EnvMetric[] = ["temperature", "humidity", "sound_level"];
const META: Record<EnvMetric, { label: string; unit: string; color: string; icon: typeof Thermometer; the: string; of: string; to: string }> = {
  temperature: { label: "Température", unit: "°C", color: "#d98519", icon: Thermometer, the: "la température", of: "de la température", to: "à la température" },
  humidity: { label: "Humidité", unit: "%", color: "#2184a7", icon: Droplets, the: "l’humidité", of: "de l’humidité", to: "à l’humidité" },
  sound_level: { label: "Niveau sonore", unit: "dBA", color: "#7259bd", icon: Volume2, the: "le niveau sonore", of: "du niveau sonore", to: "au niveau sonore" },
};
/** Nombre minimal de créneaux communs pour calculer une corrélation. */
const MIN_POINTS = 8;
/** Décalage maximal testé (en nombre de créneaux) pour détecter un effet retardé. */
const MAX_LAG = 4;

/* ------------------------------------------------------------------ */
/* Statistiques                                                        */
/* ------------------------------------------------------------------ */

interface Series { type: EnvMetric; unit: string; bucketMinutes: number; values: Map<number, number>; times: Map<number, string> }

interface PairResult {
  a: EnvMetric;
  b: EnvMetric;
  n: number;
  r: number | null;
  pValue: number | null;
  slope: number | null;
  intercept: number | null;
  points: { x: number; y: number; time: string }[];
  bestLag: { lag: number; r: number } | null;
  /** Corrélation partielle en neutralisant la troisième mesure (si disponible). */
  partial: { control: EnvMetric; r: number } | null;
}

function pearson(xs: number[], ys: number[]) {
  const n = xs.length;
  if (n < 3) return null;
  const mx = xs.reduce((s, v) => s + v, 0) / n;
  const my = ys.reduce((s, v) => s + v, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) { const dx = xs[i] - mx; const dy = ys[i] - my; sxy += dx * dy; sxx += dx * dx; syy += dy * dy; }
  if (sxx === 0 || syy === 0) return null; // une des séries est constante
  const r = sxy / Math.sqrt(sxx * syy);
  const slope = sxy / sxx;
  return { r: Math.max(-1, Math.min(1, r)), slope, intercept: my - slope * mx };
}

/** Fonction d'erreur (approximation d'Abramowitz & Stegun 7.1.26). */
function erf(x: number) {
  const sign = Math.sign(x); const t = 1 / (1 + 0.3275911 * Math.abs(x));
  const y = 1 - ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x);
  return sign * y;
}

/** Valeur p bilatérale via la transformation de Fisher (approximation). */
function pValueFor(r: number, n: number) {
  if (n < 4) return null;
  const clamped = Math.max(-0.999999, Math.min(0.999999, r));
  const z = Math.abs(Math.atanh(clamped)) * Math.sqrt(n - 3);
  return Math.max(0, 1 - erf(z / Math.SQRT2));
}

function toSeries(history: ZoneHistory, type: EnvMetric): Series {
  const bucketMinutes = history.bucket_minutes || 15;
  const bucketMs = bucketMinutes * 60_000;
  const values = new Map<number, number>(); const times = new Map<number, string>();
  history.points.forEach((point) => {
    const ts = Date.parse(point.time);
    if (!Number.isFinite(ts) || point.average == null || !Number.isFinite(point.average) || point.count === 0) return;
    const key = Math.round(ts / bucketMs);
    values.set(key, point.average); times.set(key, point.time);
  });
  return { type, unit: history.unit || META[type].unit, bucketMinutes, values, times };
}

function pairValues(a: Series, b: Series, lag = 0) {
  const xs: number[] = []; const ys: number[] = []; const keys: number[] = [];
  a.values.forEach((x, key) => { const y = b.values.get(key + lag); if (y != null) { xs.push(x); ys.push(y); keys.push(key); } });
  return { xs, ys, keys };
}

function analysePair(a: Series, b: Series): PairResult {
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
    a: a.type, b: b.type, n: xs.length,
    r: fit?.r ?? null,
    pValue: fit ? pValueFor(fit.r, xs.length) : null,
    slope: fit?.slope ?? null, intercept: fit?.intercept ?? null,
    points: xs.map((x, i) => ({ x, y: ys[i], time: a.times.get(keys[i]) || "" })),
    bestLag,
    partial: null,
  };
}

/** Ajoute la corrélation partielle r(a,b | c) pour détecter les liens indirects. */
function withPartials(pairs: PairResult[]) {
  const r = (x: EnvMetric, y: EnvMetric) => pairs.find((p) => (p.a === x && p.b === y) || (p.a === y && p.b === x))?.r ?? null;
  return pairs.map((pair) => {
    const control = ENV_METRICS.find((m) => m !== pair.a && m !== pair.b);
    if (!control || pair.r == null) return pair;
    const rac = r(pair.a, control); const rbc = r(pair.b, control);
    if (rac == null || rbc == null) return pair;
    const denom = Math.sqrt((1 - rac * rac) * (1 - rbc * rbc));
    if (denom < 1e-6) return pair;
    return { ...pair, partial: { control, r: Math.max(-1, Math.min(1, (pair.r - rac * rbc) / denom)) } };
  });
}
/** Lien apparent qui disparaît quand on neutralise la troisième mesure. */
function isIndirect(pair: PairResult) { return isMeaningful(pair) && pair.partial != null && Math.abs(pair.partial.r) < 0.3; }

/* ------------------------------------------------------------------ */
/* Interprétation                                                      */
/* ------------------------------------------------------------------ */

function strengthOf(r: number) {
  const v = Math.abs(r);
  if (v < 0.2) return { label: "Très faible", level: 0 };
  if (v < 0.4) return { label: "Faible", level: 1 };
  if (v < 0.6) return { label: "Modérée", level: 2 };
  if (v < 0.8) return { label: "Forte", level: 3 };
  return { label: "Très forte", level: 4 };
}
function isMeaningful(pair: PairResult) { return pair.r != null && Math.abs(pair.r) >= 0.4 && (pair.pValue ?? 1) < 0.05; }
function pairKey(a: EnvMetric, b: EnvMetric) { return `${a}|${b}`; }
function pairLabel(pair: PairResult) { return `${META[pair.a].label} ↔ ${META[pair.b].label}`; }
function fmt(value: number, digits = 2) { return new Intl.NumberFormat("fr-CA", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value); }
function signed(value: number, digits = 2) { return `${value > 0 ? "+" : value < 0 ? "−" : ""}${fmt(Math.abs(value), digits)}`; }
function formatP(p: number | null) { if (p == null) return "—"; if (p < 0.001) return "< 0,001"; return fmt(p, 3); }

const PHYSICS: Record<string, { positive: string; negative: string }> = {
  [pairKey("temperature", "humidity")]: {
    negative: "Quand la température monte, l’humidité relative baisse. C’est le comportement physique attendu : à quantité de vapeur d’eau constante, un air plus chaud affiche une humidité relative plus faible. Les variations d’humidité s’expliquent donc surtout par la température, et non par un apport ou une perte d’eau.",
    positive: "Température et humidité montent ensemble : un apport de vapeur d’eau accompagne la chaleur (respiration des occupants, air extérieur chaud et humide, ventilation insuffisante). Ce n’est pas l’effet physique habituel, ce qui pointe vers une source d’humidité dans l’espace.",
  },
  [pairKey("temperature", "sound_level")]: {
    positive: "Les périodes bruyantes sont aussi les plus chaudes : une même activité (personnes présentes, équipements en marche) produit à la fois du bruit et de la chaleur.",
    negative: "Le bruit augmente quand la température baisse : cela peut indiquer un système de ventilation ou de climatisation audible qui se met en marche pour refroidir l’espace.",
  },
  [pairKey("humidity", "sound_level")]: {
    positive: "Bruit et humidité augmentent ensemble : la présence de personnes (conversations et respiration) est l’explication la plus probable.",
    negative: "Le bruit monte quand l’humidité baisse : la ventilation renouvelle probablement l’air (bruit de soufflage) tout en l’asséchant.",
  },
};

function pairConclusion(pair: PairResult, bucketMinutes: number) {
  if (pair.n < MIN_POINTS) return `Pas assez de créneaux communs (${pair.n}) pour conclure. Il en faut au moins ${MIN_POINTS}.`;
  if (pair.r == null) return "Une des deux mesures est restée constante sur la période : la corrélation n’est pas calculable.";
  const strength = strengthOf(pair.r);
  const direction = pair.r > 0 ? "positive" : "négative";
  let text: string;
  if (!isMeaningful(pair)) {
    text = `Corrélation ${strength.label.toLowerCase()} (r = ${signed(pair.r)}) : pas de lien notable. Ces deux grandeurs évoluent de façon largement indépendante sur la période et sont pilotées par des causes différentes.`;
  } else if (isIndirect(pair)) {
    const c = META[pair.partial!.control];
    text = `Corrélation ${direction} ${strength.label.toLowerCase()} en apparence (r = ${signed(pair.r)}), mais ce lien est indirect : une fois l’effet ${c.of} retiré, il tombe à r = ${signed(pair.partial!.r)}. Ces deux mesures ne s’influencent pas directement ; elles réagissent toutes les deux ${c.to}.`;
  } else {
    const physics = PHYSICS[pairKey(pair.a, pair.b)]?.[pair.r > 0 ? "positive" : "negative"] ?? "";
    const share = Math.round(pair.r * pair.r * 100);
    const slope = pair.slope != null ? ` En moyenne, +1 ${META[pair.a].unit} ${META[pair.a].of} correspond à ${signed(pair.slope, 1)} ${META[pair.b].unit} ${META[pair.b].of}.` : "";
    const direct = pair.partial && Math.abs(pair.partial.r) >= 0.3 ? ` Le lien reste présent même en neutralisant ${META[pair.partial.control].the} (r partiel = ${signed(pair.partial.r)}) : il est direct.` : "";
    text = `Corrélation ${direction} ${strength.label.toLowerCase()} (r = ${signed(pair.r)}) : environ ${share} % des variations de l’une sont associées à celles de l’autre.${slope} ${physics}${direct}`;
  }
  if (pair.bestLag) {
    const minutes = Math.abs(pair.bestLag.lag) * bucketMinutes;
    const leader = META[pair.bestLag.lag > 0 ? pair.a : pair.b];
    const follower = META[pair.bestLag.lag > 0 ? pair.b : pair.a];
    text += ` Le lien est plus net avec un décalage : ${follower.the} réagit environ ${minutes} min après ${leader.the} (r = ${signed(pair.bestLag.r)}).`;
  }
  return text;
}

function synthesis(pairs: PairResult[], available: EnvMetric[]) {
  const items: string[] = [];
  const valid = pairs.filter((p) => p.r != null && p.n >= MIN_POINTS);
  if (!valid.length) return ["Les données disponibles ne permettent pas encore de tirer de conclusion sur les liens entre les systèmes. Choisissez une journée plus complète ou la période de 7 jours."];
  const get = (a: EnvMetric, b: EnvMetric) => valid.find((p) => p.a === a && p.b === b);
  const direct = (p?: PairResult) => !!p && isMeaningful(p) && !isIndirect(p);
  const meaningful = valid.filter(isMeaningful);
  const strongest = [...valid].sort((x, y) => Math.abs(y.r!) - Math.abs(x.r!))[0];

  if (!meaningful.length) {
    items.push(`Aucun lien significatif entre ${available.map((m) => META[m].label.toLowerCase()).join(", ").replace(/, ([^,]*)$/, " et $1")} sur cette période : chaque système évolue indépendamment. Une alerte sur l’un ne permet pas d’anticiper l’autre ; il faut les surveiller séparément.`);
  } else {
    items.push(`Le lien le plus marqué est ${pairLabel(strongest).toLowerCase()} (r = ${signed(strongest.r!)}, ${strengthOf(strongest.r!).label.toLowerCase()}).`);
  }

  const th = get("temperature", "humidity");
  if (th && direct(th) && th.r! < 0) items.push("L’humidité relative est principalement pilotée par la température. Pour la stabiliser, il est plus efficace de stabiliser d’abord le chauffage ou la climatisation que d’agir sur un humidificateur.");
  if (th && direct(th) && th.r! > 0) items.push("Chaleur et humidité augmentent ensemble : vérifier le renouvellement d’air, surtout lors des périodes de forte présence.");

  const ts = get("temperature", "sound_level"); const hs = get("humidity", "sound_level");
  const tsPos = direct(ts) && ts!.r! > 0; const hsPos = direct(hs) && hs!.r! > 0;
  if (tsPos && hsPos) items.push("Le niveau sonore évolue avec la température et l’humidité : l’occupation de l’espace est très probablement le facteur commun. Augmenter la ventilation pendant les périodes d’activité limiterait la hausse de chaleur et d’humidité.");
  else if (tsPos || hsPos) items.push("Le bruit, indicateur indirect de présence, est lié à au moins une mesure climatique : l’activité humaine influence l’ambiance de cet espace.");
  if (direct(ts) && ts!.r! < 0) items.push("Le bruit associé aux baisses de température suggère un équipement de ventilation audible : à vérifier si le confort acoustique est une priorité.");
  if (available.includes("sound_level") && ts && hs && !isMeaningful(ts) && !isMeaningful(hs)) items.push("Le niveau sonore n’influence pas le climat de l’espace sur cette période : les sources de bruit sont ponctuelles ou ne correspondent pas à une présence prolongée.");

  valid.filter(isIndirect).forEach((p) => items.push(`Le lien ${pairLabel(p).toLowerCase()} n’est qu’un effet indirect ${META[p.partial!.control].of} : inutile d’agir sur l’une de ces deux mesures pour corriger l’autre, c’est ${META[p.partial!.control].the} qu’il faut surveiller.`));
  const lagged = valid.find((p) => p.bestLag);
  if (lagged) items.push("Un effet retardé a été détecté (voir le détail ci-dessus) : une mesure peut servir d’indicateur précoce pour l’autre et permettre d’anticiper une alerte.");
  return items;
}

/* ------------------------------------------------------------------ */
/* Composants                                                          */
/* ------------------------------------------------------------------ */

function rColor(r: number | null) {
  if (r == null) return "#8a9692";
  const v = Math.min(1, Math.abs(r));
  // Échelle divergente : bleu (négatif) ↔ orange brûlé (positif), plus foncé quand |r| est grand.
  const light = 72 - v * 34;
  return r < 0 ? `hsl(200 62% ${light}%)` : `hsl(14 62% ${light}%)`;
}

function PairCard({ pair }: { pair: PairResult }) {
  const A = META[pair.a].icon; const B = META[pair.b].icon;
  const strength = pair.r != null ? strengthOf(pair.r) : null;
  const position = pair.r != null ? ((pair.r + 1) / 2) * 100 : 50;
  return <div className="corr-pair">
    <div className="corr-pair-head"><span style={{ color: META[pair.a].color }}><A size={15} /></span><ArrowRightLeft size={12} className="corr-arrow" /><span style={{ color: META[pair.b].color }}><B size={15} /></span><strong>{pairLabel(pair)}</strong></div>
    <div className="corr-r"><strong style={{ color: rColor(pair.r) }}>{pair.r != null ? signed(pair.r) : "—"}</strong>{strength && <em className={`strength strength-${strength.level}`}>{strength.label}{pair.r != null && Math.abs(pair.r) >= 0.2 ? (pair.r > 0 ? " · positive" : " · négative") : ""}</em>}</div>
    <div className="corr-scale" aria-hidden="true"><i style={{ left: `${position}%`, background: rColor(pair.r) }} /></div>
    <div className="corr-scale-labels"><span>−1</span><span>0</span><span>+1</span></div>
    <dl><div><dt>Créneaux</dt><dd>{pair.n}</dd></div><div><dt>r²</dt><dd>{pair.r != null ? `${Math.round(pair.r * pair.r * 100)} %` : "—"}</dd></div><div><dt>Valeur p</dt><dd>{formatP(pair.pValue)}</dd></div></dl>
    {isIndirect(pair) && <span className="corr-indirect">Lien indirect · via {META[pair.partial!.control].the}</span>}
  </div>;
}

function Matrix({ metrics, pairs }: { metrics: EnvMetric[]; pairs: PairResult[] }) {
  const find = (a: EnvMetric, b: EnvMetric) => pairs.find((p) => (p.a === a && p.b === b) || (p.a === b && p.b === a));
  return <div className="corr-matrix" style={{ gridTemplateColumns: `minmax(92px,auto) repeat(${metrics.length}, minmax(0,1fr))` }}>
    <span />{metrics.map((m) => <span key={m} className="corr-matrix-label">{META[m].label}</span>)}
    {metrics.map((row) => <div className="corr-matrix-row" key={row} style={{ display: "contents" }}>
      <span className="corr-matrix-label row">{META[row].label}</span>
      {metrics.map((col) => { const r = row === col ? 1 : find(row, col)?.r ?? null; return <div key={col} className={`corr-cell ${row === col ? "diag" : ""}`} style={{ background: row === col ? undefined : rColor(r), color: r != null && Math.abs(r) > 0.45 && row !== col ? "#fff" : undefined }}>{row === col ? "1" : r != null ? signed(r) : "—"}</div>; })}
    </div>)}
  </div>;
}

function PairScatter({ pair }: { pair: PairResult }) {
  const a = META[pair.a]; const b = META[pair.b];
  const xs = pair.points.map((p) => p.x);
  const xMin = Math.min(...xs); const xMax = Math.max(...xs);
  const line: [{ x: number; y: number }, { x: number; y: number }] | null = pair.slope != null && pair.intercept != null && xMin < xMax ? [{ x: xMin, y: pair.intercept + pair.slope * xMin }, { x: xMax, y: pair.intercept + pair.slope * xMax }] : null;
  return <div className="corr-scatter">
    <div className="corr-scatter-title"><strong>{pairLabel(pair)}</strong><small>Chaque point = un créneau · ligne = tendance linéaire</small></div>
    <div className="corr-scatter-chart">{pair.points.length >= 3 ? <ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{ top: 8, right: 14, bottom: 18, left: 4 }}>
      <CartesianGrid stroke="#dfe7e4" strokeDasharray="3 5" />
      <XAxis type="number" dataKey="x" name={a.label} domain={["auto", "auto"]} tick={{ fill: "#64716d", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v: number) => fmt(v, 1)} label={{ value: `${a.label} (${a.unit})`, position: "insideBottom", offset: -10, fill: "#64716d", fontSize: 11 }} />
      <YAxis type="number" dataKey="y" name={b.label} domain={["auto", "auto"]} tick={{ fill: "#64716d", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v: number) => fmt(v, 0)} width={52} label={{ value: `${b.label} (${b.unit})`, angle: -90, position: "insideLeft", offset: 14, dy: 50, fill: "#64716d", fontSize: 11 }} />
      <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(value, name) => [`${fmt(Number(value), 1)} ${name === a.label ? a.unit : b.unit}`, String(name)]} />
      <Scatter data={pair.points} fill={b.color} fillOpacity={0.55} />
      {line && <ReferenceLine segment={line} stroke="#18201e" strokeWidth={1.6} strokeDasharray="5 4" ifOverflow="extendDomain" />}
    </ScatterChart></ResponsiveContainer> : <div className="chart-empty">Pas assez de points communs.</div>}</div>
  </div>;
}

function NormalizedOverlay({ series, period }: { series: Series[]; period: Period }) {
  const data = useMemo(() => {
    const stats = series.map((s) => { const vals = [...s.values.values()]; const mean = vals.reduce((x, y) => x + y, 0) / vals.length; const sd = Math.sqrt(vals.reduce((x, y) => x + (y - mean) ** 2, 0) / vals.length) || 1; return { s, mean, sd }; });
    const keys = Array.from(new Set(series.flatMap((s) => [...s.values.keys()]))).sort((x, y) => x - y);
    return keys.map((key) => {
      const row: Record<string, number | string | null> = { time: series.map((s) => s.times.get(key)).find(Boolean) || "" };
      stats.forEach(({ s, mean, sd }) => { const v = s.values.get(key); row[s.type] = v == null ? null : Math.round(((v - mean) / sd) * 100) / 100; });
      return row;
    });
  }, [series]);
  const timeFormat = period === "day" ? { hour: "2-digit", minute: "2-digit" } as const : { weekday: "short", hour: "2-digit" } as const;
  return <div className="corr-overlay">
    <div className="corr-scatter-title"><strong>Évolution comparée (valeurs normalisées)</strong><small>0 = moyenne de la période · ±1 = un écart-type. Des courbes qui bougent ensemble indiquent une corrélation.</small></div>
    <div className="corr-legend">{series.map((s) => <span key={s.type}><i style={{ background: META[s.type].color }} />{META[s.type].label}</span>)}</div>
    <div className="corr-overlay-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 8, right: 14, left: -18, bottom: 0 }}>
      <CartesianGrid stroke="#dfe7e4" strokeDasharray="3 5" vertical={false} />
      <XAxis dataKey="time" axisLine={false} tickLine={false} minTickGap={40} tick={{ fill: "#64716d", fontSize: 11 }} tickFormatter={(v) => (v ? new Intl.DateTimeFormat("fr-CA", timeFormat).format(new Date(String(v))) : "")} />
      <YAxis axisLine={false} tickLine={false} tick={{ fill: "#64716d", fontSize: 11 }} domain={[-3, 3]} allowDataOverflow ticks={[-2, -1, 0, 1, 2]} />
      <ReferenceLine y={0} stroke="#9aa7a3" />
      <Tooltip labelFormatter={(v) => (v ? new Intl.DateTimeFormat("fr-CA", { weekday: "long", hour: "2-digit", minute: "2-digit" }).format(new Date(String(v))) : "")} formatter={(value, name) => [value == null ? "—" : `${signed(Number(value), 2)} σ`, META[name as EnvMetric]?.label ?? String(name)]} />
      {series.map((s) => <Line key={s.type} type="monotone" dataKey={s.type} stroke={META[s.type].color} strokeWidth={2} dot={false} connectNulls />)}
    </LineChart></ResponsiveContainer></div>
  </div>;
}

export function CorrelationPanel({ zoneCode, zoneName, selectedDate }: { zoneCode: string; zoneName?: string; selectedDate: string }) {
  const [period, setPeriod] = useState<Period>("day");
  const [series, setSeries] = useState<Series[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isOccupancyOnly = zoneName === "occupancy-camera";

  useEffect(() => {
    if (!zoneCode || isOccupancyOnly) return;
    let cancelled = false; setLoading(true); setError(null); setSeries(null);
    const load = (type: EnvMetric) => (period === "day" ? loadZoneDayHistory(zoneCode, type, selectedDate) : loadZoneHistory(zoneCode, type, 168)).then((h) => toSeries(h, type)).catch(() => null);
    void Promise.all(ENV_METRICS.map(load)).then((result) => {
      if (cancelled) return;
      setSeries(result.filter((s): s is Series => s != null && s.values.size >= MIN_POINTS));
    }).catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : "Analyse indisponible."); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [zoneCode, selectedDate, period, isOccupancyOnly]);

  const available = useMemo(() => (series || []).map((s) => s.type), [series]);
  const pairs = useMemo(() => {
    const list: PairResult[] = []; const s = series || [];
    for (let i = 0; i < s.length; i++) for (let j = i + 1; j < s.length; j++) list.push(analysePair(s[i], s[j]));
    return withPartials(list);
  }, [series]);
  const bucketMinutes = series?.[0]?.bucketMinutes ?? 15;
  const conclusions = useMemo(() => synthesis(pairs, available), [pairs, available]);
  const periodLabel = period === "day" ? new Intl.DateTimeFormat("fr-CA", { weekday: "long", day: "numeric", month: "long" }).format(new Date(`${selectedDate}T12:00:00`)) : "7 derniers jours";
  const periodTitle = periodLabel.charAt(0).toUpperCase() + periodLabel.slice(1);

  let body: ReactNode;
  if (isOccupancyOnly) body = <div className="corr-empty">Cet espace ne mesure que l’occupation. Les corrélations température, humidité et niveau sonore sont disponibles dans les autres espaces.</div>;
  else if (loading) body = <div className="corr-empty">Calcul des corrélations…</div>;
  else if (error) body = <div className="corr-empty">{error}</div>;
  else if (!series || series.length < 2) body = <div className="corr-empty">Il faut au moins deux mesures avec {MIN_POINTS} créneaux ou plus pour calculer une corrélation.{series?.length === 1 ? ` Seule la mesure « ${META[series[0].type].label} » est disponible pour ${periodLabel}.` : ""}{period === "day" ? " Essayez la période de 7 jours." : ""}</div>;
  else body = <>
    <div className="corr-top">
      <div className="corr-pairs">{pairs.map((p) => <PairCard key={pairKey(p.a, p.b)} pair={p} />)}</div>
      {available.length > 2 && <div className="corr-matrix-card"><span className="corr-sub">Matrice de corrélation</span><Matrix metrics={available} pairs={pairs} /><div className="corr-matrix-legend"><span>Négative</span><i /><span>Positive</span></div></div>}
    </div>
    <NormalizedOverlay series={series} period={period} />
    <div className="corr-scatters">{pairs.map((p) => <PairScatter key={pairKey(p.a, p.b)} pair={p} />)}</div>
    <div className="corr-conclusions">
      <h4><Lightbulb size={17} /> Conclusions</h4>
      <div className="corr-conclusion-list">{pairs.map((p) => <div className="corr-conclusion" key={pairKey(p.a, p.b)}><strong>{pairLabel(p)}</strong><p>{pairConclusion(p, bucketMinutes)}</p></div>)}</div>
      <div className="corr-synthesis"><strong>Synthèse pour {zoneName === "occupancy-camera" ? "GRIDD" : zoneName} · {periodLabel}</strong><ul>{conclusions.map((c, i) => <li key={i}>{c}</li>)}</ul></div>
      <p className="corr-note"><Info size={13} /> Coefficient de Pearson calculé sur les moyennes par créneau de {bucketMinutes} min. Une corrélation indique que deux mesures varient ensemble, pas que l’une cause l’autre. La valeur p est indicative : des mesures consécutives ne sont pas totalement indépendantes.</p>
    </div>
  </>;

  return <section className="corr-card">
    <div className="corr-head">
      <div><span className="section-kicker"><GitCompareArrows size={13} /> Corrélations entre systèmes</span><h3>Température, humidité et niveau sonore</h3><p>Comment les mesures de cet espace évoluent les unes par rapport aux autres · <span className="corr-period">{periodTitle}</span></p></div>
      {!isOccupancyOnly && <div className="corr-toggle" role="group" aria-label="Période d’analyse"><button type="button" className={period === "day" ? "active" : ""} onClick={() => setPeriod("day")}>Jour sélectionné</button><button type="button" className={period === "week" ? "active" : ""} onClick={() => setPeriod("week")}>7 derniers jours</button></div>}
    </div>
    {body}
  </section>;
}
