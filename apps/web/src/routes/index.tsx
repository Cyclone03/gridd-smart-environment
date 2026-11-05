import type { ComponentType } from "react";
import type { RouteObject } from "react-router";
import { AppLayout } from "../layouts/AppLayout";
import { AlarmRuleEditView } from "../views/AlarmRuleEditView";
import { AlarmRulesView } from "../views/AlarmRulesView";
import { AlertsView } from "../views/AlertsView";
import { ComfortView } from "../views/ComfortView";
import { EnergyView } from "../views/EnergyView";
import { HistoryView } from "../views/HistoryView";
import { NotFoundView } from "../views/NotFoundView";
import { OverviewView } from "../views/OverviewView";
import { SpacesView } from "../views/SpacesView";
import { ROUTE_DEFINITIONS, type RouteName } from "./definitions";
import { RouteTitle } from "./RouteTitle";

/** Vue associée à chaque route nommée (voir ./definitions.ts). */
const VIEWS: Record<RouteName, ComponentType> = {
  overview: OverviewView,
  spaces: SpacesView,
  comfort: ComfortView,
  energy: EnergyView,
  history: HistoryView,
  alerts: AlertsView,
  alarmRules: AlarmRulesView,
  alarmRuleCreate: AlarmRuleEditView,
  alarmRuleEdit: AlarmRuleEditView,
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
          <RouteTitle definition={definition}>
            <View />
          </RouteTitle>
        ),
      };
    }),
  },
];
