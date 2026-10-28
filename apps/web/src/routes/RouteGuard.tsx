import { useEffect, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { Loading } from "../components/common/Feedback";
import { APP_NAME } from "../constants/app";
import { useAuth } from "../stores/authStore";
import type { RouteDefinition } from "./definitions";

/**
 * Applique les métadonnées (titre) et la règle d'accès d'une route.
 * Sans session : redirection vers la connexion avec retour automatique.
 */
export function RouteGuard({ definition, children }: { definition: RouteDefinition; children: ReactNode }) {
  const { user, initializing, can } = useAuth();
  const location = useLocation();

  useEffect(() => {
    document.title = `${definition.meta.title} · ${APP_NAME}`;
  }, [definition.meta.title]);

  if (definition.access.kind === "permission") {
    if (initializing) return <Loading label="Vérification de la session…" />;
    if (!user) {
      const next = encodeURIComponent(location.pathname + location.search);
      return <Navigate to={`/login?next=${next}`} replace />;
    }
    if (!can(definition.access.permission))
      return (
        <main className="dashboard page-view narrow">
          <div className="error-banner" role="alert">
            Accès refusé : votre compte n’a pas les droits nécessaires pour cette page.
          </div>
        </main>
      );
  }
  return <>{children}</>;
}
