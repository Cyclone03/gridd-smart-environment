import { useEffect, type ReactNode } from "react";
import { APP_NAME } from "../constants/app";
import type { RouteDefinition } from "./definitions";

/** Applique les métadonnées d'une route (titre de l'onglet). */
export function RouteTitle({ definition, children }: { definition: RouteDefinition; children: ReactNode }) {
  useEffect(() => {
    document.title = `${definition.meta.title} · ${APP_NAME}`;
  }, [definition.meta.title]);
  return <>{children}</>;
}
