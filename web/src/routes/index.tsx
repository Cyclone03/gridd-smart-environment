import type { ComponentType } from "react";
import type { RouteObject } from "react-router";
import { AppLayout } from "../layouts/AppLayout";
import { AlarmRuleEditView } from "../views/AlarmRuleEditView";
import { AlarmRulesView } from "../views/AlarmRulesView";
import { AlertsView } from "../views/AlertsView";
import { HistoryView } from "../views/HistoryView";
import { LoginView } from "../views/LoginView";
import { NotFoundView } from "../views/NotFoundView";
import { OverviewView } from "../views/OverviewView";
import { SpacesView } from "../views/SpacesView";
import { ROUTE_DEFINITIONS, type RouteName } from "./definitions";
import { RouteGuard } from "./RouteGuard";

/** Vue associée à chaque route nommée (voir ./definitions.ts). */
const VIEWS: Record<RouteName, ComponentType> = {
  overview: OverviewView,
  spaces: SpacesView,
  history: HistoryView,
  alerts: AlertsView,
  alarmRules: AlarmRulesView,
  alarmRuleCreate: AlarmRuleEditView,
  alarmRuleEdit: AlarmRuleEditView,
  login: LoginView,
  notFound: NotFoundView,
};

/** Arbre de routes utilisé par le routeur du navigateur et par les tests. */
export const routes: RouteObject[] = [
  {
    element: <AppLayout />,
    children: ROUTE_DEFINITIONS.map((definition) => {
      const View = VIEWS[definition.name];
      return {
        id: definition.name,
        path: definition.path,
        handle: definition,
        element: (
          <RouteGuard definition={definition}>
            <View />
          </RouteGuard>
        ),
      };
    }),
  },
];
