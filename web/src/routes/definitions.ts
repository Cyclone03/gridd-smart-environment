/**
 * Table des routes de l'application : nom, chemin et métadonnées. Les vues
 * associées sont déclarées dans ./index.tsx.
 */

export type RouteName =
  | "overview"
  | "spaces"
  | "comfort"
  | "energy"
  | "history"
  | "alerts"
  | "alarmRules"
  | "alarmRuleCreate"
  | "alarmRuleEdit"
  | "notFound";

export interface RouteMeta {
  /** Titre de l'onglet du navigateur. */
  title: string;
  /** Libellé dans la navigation principale (absent = non affiché). */
  navLabel?: string;
}

export interface RouteDefinition {
  name: RouteName;
  path: string;
  meta: RouteMeta;
}

export const ROUTE_DEFINITIONS: RouteDefinition[] = [
  { name: "overview", path: "/", meta: { title: "Vue d'ensemble", navLabel: "Vue d’ensemble" } },
  { name: "spaces", path: "/spaces", meta: { title: "Espaces", navLabel: "Espaces" } },
  { name: "comfort", path: "/comfort", meta: { title: "Confort thermique", navLabel: "Confort" } },
  { name: "energy", path: "/energy", meta: { title: "Consommation énergétique", navLabel: "Énergie" } },
  { name: "history", path: "/history", meta: { title: "Analyse historique", navLabel: "Historique" } },
  { name: "alerts", path: "/alerts", meta: { title: "Alertes", navLabel: "Alertes" } },
  { name: "alarmRules", path: "/alarms/rules", meta: { title: "Règles d'alarme", navLabel: "Règles d’alarme" } },
  { name: "alarmRuleCreate", path: "/alarms/rules/new", meta: { title: "Nouvelle règle d'alarme" } },
  { name: "alarmRuleEdit", path: "/alarms/rules/:ruleId/edit", meta: { title: "Modifier une règle d'alarme" } },
  { name: "notFound", path: "*", meta: { title: "Page introuvable" } },
];

export function navigationRoutes(): (RouteDefinition & { meta: Required<RouteMeta> })[] {
  return ROUTE_DEFINITIONS.filter((route): route is RouteDefinition & { meta: Required<RouteMeta> } =>
    Boolean(route.meta.navLabel),
  );
}

/** Construit le chemin d'une route nommée : `routePath("alarmRuleEdit", { ruleId: 4 })`. */
export function routePath(name: RouteName, params: Record<string, string | number> = {}): string {
  const definition = ROUTE_DEFINITIONS.find((route) => route.name === name);
  if (!definition) throw new Error(`Route inconnue : ${name}`);
  return definition.path.replace(/:(\w+)/g, (_match, key: string) => encodeURIComponent(String(params[key])));
}
