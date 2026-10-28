/**
 * Table des routes de l'application : nom, chemin, métadonnées et règles
 * d'accès. Les vues associées sont déclarées dans ./index.tsx.
 *
 * Les règles d'accès ne servent qu'à l'ergonomie (redirection vers la
 * connexion, masquage des actions) : l'API vérifie elle-même les droits.
 */
import type { Permission } from "../resources/auth";

export type RouteName =
  | "overview"
  | "spaces"
  | "history"
  | "alerts"
  | "alarmRules"
  | "alarmRuleCreate"
  | "alarmRuleEdit"
  | "login"
  | "notFound";

export type RouteAccess = { kind: "public" } | { kind: "permission"; permission: Permission };

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
  access: RouteAccess;
}

const PUBLIC: RouteAccess = { kind: "public" };

export const ROUTE_DEFINITIONS: RouteDefinition[] = [
  { name: "overview", path: "/", meta: { title: "Vue d'ensemble", navLabel: "Vue d’ensemble" }, access: PUBLIC },
  { name: "spaces", path: "/spaces", meta: { title: "Espaces", navLabel: "Espaces" }, access: PUBLIC },
  {
    name: "history",
    path: "/history",
    meta: { title: "Analyse historique", navLabel: "Analyse historique" },
    access: PUBLIC,
  },
  { name: "alerts", path: "/alerts", meta: { title: "Alertes", navLabel: "Alertes" }, access: PUBLIC },
  {
    name: "alarmRules",
    path: "/alarms/rules",
    meta: { title: "Règles d'alarme", navLabel: "Règles d’alarme" },
    access: PUBLIC,
  },
  {
    name: "alarmRuleCreate",
    path: "/alarms/rules/new",
    meta: { title: "Nouvelle règle d'alarme" },
    access: { kind: "permission", permission: "alarm_rules.add" },
  },
  {
    name: "alarmRuleEdit",
    path: "/alarms/rules/:ruleId/edit",
    meta: { title: "Modifier une règle d'alarme" },
    access: { kind: "permission", permission: "alarm_rules.change" },
  },
  { name: "login", path: "/login", meta: { title: "Connexion" }, access: PUBLIC },
  { name: "notFound", path: "*", meta: { title: "Page introuvable" }, access: PUBLIC },
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
