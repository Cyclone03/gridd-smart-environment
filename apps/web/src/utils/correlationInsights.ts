/**
 * Interprétation en français des corrélations calculées par ./correlation.ts.
 * Les explications physiques sont des pistes de lecture, pas des diagnostics.
 */
import { METRIC_UNITS, METRIC_VISUALS, type CorrelationMetric } from "../constants/metrics";
import { isIndirect, isMeaningful, MIN_POINTS, pairKey, strengthOf, type PairResult } from "./correlation";
import { formatNumber } from "./format";

/** Formes grammaticales utilisées dans les phrases générées. */
const GRAMMAR: Record<CorrelationMetric, { the: string; of: string; to: string }> = {
  temperature: { the: "la température", of: "de la température", to: "à la température" },
  humidity: { the: "l’humidité", of: "de l’humidité", to: "à l’humidité" },
  sound_level: { the: "le niveau sonore", of: "du niveau sonore", to: "au niveau sonore" },
};

const label = (metric: CorrelationMetric) => METRIC_VISUALS[metric].label;

export function signed(value: number, digits = 2) {
  return `${value > 0 ? "+" : value < 0 ? "−" : ""}${formatNumber(Math.abs(value), digits)}`;
}

export function formatP(p: number | null) {
  if (p == null) return "—";
  if (p < 0.001) return "< 0,001";
  return formatNumber(p, 3);
}

export function pairLabel(pair: PairResult) {
  return `${label(pair.a)} ↔ ${label(pair.b)}`;
}

export function controlPhrase(metric: CorrelationMetric) {
  return GRAMMAR[metric].the;
}

const PHYSICS: Record<string, { positive: string; negative: string }> = {
  [pairKey("temperature", "humidity")]: {
    negative:
      "Quand la température monte, l’humidité relative baisse. C’est le comportement physique attendu : à quantité de vapeur d’eau constante, un air plus chaud affiche une humidité relative plus faible. Les variations d’humidité s’expliquent donc surtout par la température, et non par un apport ou une perte d’eau.",
    positive:
      "Température et humidité montent ensemble : un apport de vapeur d’eau accompagne la chaleur (respiration des occupants, air extérieur chaud et humide, ventilation insuffisante). Ce n’est pas l’effet physique habituel, ce qui pointe vers une source d’humidité dans l’espace.",
  },
  [pairKey("temperature", "sound_level")]: {
    positive:
      "Les périodes bruyantes sont aussi les plus chaudes : une même activité (personnes présentes, équipements en marche) produit à la fois du bruit et de la chaleur.",
    negative:
      "Le bruit augmente quand la température baisse : cela peut indiquer un système de ventilation ou de climatisation audible qui se met en marche pour refroidir l’espace.",
  },
  [pairKey("humidity", "sound_level")]: {
    positive:
      "Bruit et humidité augmentent ensemble : la présence de personnes (conversations et respiration) est l’explication la plus probable.",
    negative:
      "Le bruit monte quand l’humidité baisse : la ventilation renouvelle probablement l’air (bruit de soufflage) tout en l’asséchant.",
  },
};

export function pairConclusion(pair: PairResult, bucketMinutes: number) {
  if (pair.n < MIN_POINTS)
    return `Pas assez de créneaux communs (${pair.n}) pour conclure. Il en faut au moins ${MIN_POINTS}.`;
  if (pair.r == null)
    return "Une des deux mesures est restée constante sur la période : la corrélation n’est pas calculable.";
  const strength = strengthOf(pair.r);
  const direction = pair.r > 0 ? "positive" : "négative";
  let text: string;
  if (!isMeaningful(pair)) {
    text = `Corrélation ${strength.label.toLowerCase()} (r = ${signed(pair.r)}) : pas de lien notable. Ces deux grandeurs évoluent de façon largement indépendante sur la période et sont pilotées par des causes différentes.`;
  } else if (isIndirect(pair)) {
    const c = GRAMMAR[pair.partial!.control];
    text = `Corrélation ${direction} ${strength.label.toLowerCase()} en apparence (r = ${signed(pair.r)}), mais ce lien est indirect : une fois l’effet ${c.of} retiré, il tombe à r = ${signed(pair.partial!.r)}. Ces deux mesures ne s’influencent pas directement ; elles réagissent toutes les deux ${c.to}.`;
  } else {
    const physics = PHYSICS[pairKey(pair.a, pair.b)]?.[pair.r > 0 ? "positive" : "negative"] ?? "";
    const share = Math.round(pair.r * pair.r * 100);
    const slope =
      pair.slope != null
        ? ` En moyenne, +1 ${METRIC_UNITS[pair.a]} ${GRAMMAR[pair.a].of} correspond à ${signed(pair.slope, 1)} ${METRIC_UNITS[pair.b]} ${GRAMMAR[pair.b].of}.`
        : "";
    const direct =
      pair.partial && Math.abs(pair.partial.r) >= 0.3
        ? ` Le lien reste présent même en neutralisant ${GRAMMAR[pair.partial.control].the} (r partiel = ${signed(pair.partial.r)}) : il est direct.`
        : "";
    text = `Corrélation ${direction} ${strength.label.toLowerCase()} (r = ${signed(pair.r)}) : environ ${share} % des variations de l’une sont associées à celles de l’autre.${slope} ${physics}${direct}`;
  }
  if (pair.bestLag) {
    const minutes = Math.abs(pair.bestLag.lag) * bucketMinutes;
    const leader = GRAMMAR[pair.bestLag.lag > 0 ? pair.a : pair.b];
    const follower = GRAMMAR[pair.bestLag.lag > 0 ? pair.b : pair.a];
    text += ` Le lien est plus net avec un décalage : ${follower.the} réagit environ ${minutes} min après ${leader.the} (r = ${signed(pair.bestLag.r)}).`;
  }
  return text;
}

export function synthesis(pairs: PairResult[], available: CorrelationMetric[]) {
  const items: string[] = [];
  const valid = pairs.filter((p) => p.r != null && p.n >= MIN_POINTS);
  if (!valid.length)
    return [
      "Les données disponibles ne permettent pas encore de tirer de conclusion sur les liens entre les systèmes. Choisissez une période plus longue.",
    ];
  const get = (a: CorrelationMetric, b: CorrelationMetric) => valid.find((p) => p.a === a && p.b === b);
  const direct = (p?: PairResult) => !!p && isMeaningful(p) && !isIndirect(p);
  const meaningful = valid.filter(isMeaningful);
  const strongest = [...valid].sort((x, y) => Math.abs(y.r!) - Math.abs(x.r!))[0];

  if (!meaningful.length) {
    const names = available
      .map((m) => label(m).toLowerCase())
      .join(", ")
      .replace(/, ([^,]*)$/, " et $1");
    items.push(
      `Aucun lien significatif entre ${names} sur cette période : chaque système évolue indépendamment. Une alerte sur l’un ne permet pas d’anticiper l’autre ; il faut les surveiller séparément.`,
    );
  } else {
    items.push(
      `Le lien le plus marqué est ${pairLabel(strongest).toLowerCase()} (r = ${signed(strongest.r!)}, ${strengthOf(strongest.r!).label.toLowerCase()}).`,
    );
  }

  const th = get("temperature", "humidity");
  if (th && direct(th) && th.r! < 0)
    items.push(
      "L’humidité relative est principalement pilotée par la température. Pour la stabiliser, il est plus efficace de stabiliser d’abord le chauffage ou la climatisation que d’agir sur un humidificateur.",
    );
  if (th && direct(th) && th.r! > 0)
    items.push(
      "Chaleur et humidité augmentent ensemble : vérifier le renouvellement d’air, surtout lors des périodes de forte présence.",
    );

  const ts = get("temperature", "sound_level");
  const hs = get("humidity", "sound_level");
  const tsPos = direct(ts) && ts!.r! > 0;
  const hsPos = direct(hs) && hs!.r! > 0;
  if (tsPos && hsPos)
    items.push(
      "Le niveau sonore évolue avec la température et l’humidité : l’occupation de l’espace est très probablement le facteur commun. Augmenter la ventilation pendant les périodes d’activité limiterait la hausse de chaleur et d’humidité.",
    );
  else if (tsPos || hsPos)
    items.push(
      "Le bruit, indicateur indirect de présence, est lié à au moins une mesure climatique : l’activité humaine influence l’ambiance de cet espace.",
    );
  if (direct(ts) && ts!.r! < 0)
    items.push(
      "Le bruit associé aux baisses de température suggère un équipement de ventilation audible : à vérifier si le confort acoustique est une priorité.",
    );
  if (available.includes("sound_level") && ts && hs && !isMeaningful(ts) && !isMeaningful(hs))
    items.push(
      "Le niveau sonore n’influence pas le climat de l’espace sur cette période : les sources de bruit sont ponctuelles ou ne correspondent pas à une présence prolongée.",
    );

  valid
    .filter(isIndirect)
    .forEach((p) =>
      items.push(
        `Le lien ${pairLabel(p).toLowerCase()} n’est qu’un effet indirect ${GRAMMAR[p.partial!.control].of} : inutile d’agir sur l’une de ces deux mesures pour corriger l’autre, c’est ${GRAMMAR[p.partial!.control].the} qu’il faut surveiller.`,
      ),
    );
  if (valid.some((p) => p.bestLag))
    items.push(
      "Un effet retardé a été détecté (voir le détail ci-dessus) : une mesure peut servir d’indicateur précoce pour l’autre et permettre d’anticiper une alerte.",
    );
  return items;
}
