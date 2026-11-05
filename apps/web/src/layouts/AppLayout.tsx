import { AlertTriangle } from "lucide-react";
import { Outlet } from "react-router";
import { TopBar } from "../components/layout/TopBar";
import { useDashboard } from "../stores/dashboardStore";

/** Structure commune : en-tête, navigation, erreur globale et contenu. */
export function AppLayout() {
  const { status, unreadAlertCount, refresh, error } = useDashboard();

  return (
    <div className="app-shell">
      <a className="skip-link" href="#contenu">
        Aller au contenu
      </a>
      <TopBar status={status} unreadAlerts={unreadAlertCount} onRefresh={() => void refresh()} />
      {error && (
        <div className="global-error" role="alert">
          <AlertTriangle size={17} aria-hidden="true" />
          {error}
        </div>
      )}
      <div id="contenu">
        <Outlet />
      </div>
    </div>
  );
}
