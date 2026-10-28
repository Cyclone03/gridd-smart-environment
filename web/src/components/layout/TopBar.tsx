import { Leaf, LogIn, LogOut, RefreshCw } from "lucide-react";
import { Link, useLocation } from "react-router";
import type { AuthUser } from "../../resources/auth";
import type { RealtimeStatus } from "../../types/common";
import { StatusPill } from "../common/StatusPill";
import { MainNav } from "./MainNav";

export function TopBar({
  status,
  unreadAlerts,
  user,
  onRefresh,
  onLogout,
}: {
  status: RealtimeStatus;
  unreadAlerts: number;
  user: AuthUser | null;
  onRefresh: () => void;
  onLogout: () => void;
}) {
  const location = useLocation();
  return (
    <header className="topbar">
      <Link className="brand" to="/">
        <span className="brand-mark">
          <Leaf size={22} aria-hidden="true" />
        </span>
        <span>
          <strong>GRIDD</strong>
          <small>Smart environment</small>
        </span>
      </Link>
      <MainNav unreadAlerts={unreadAlerts} />
      <div className="topbar-actions">
        <StatusPill status={status} />
        <button className="icon-button" type="button" onClick={onRefresh} aria-label="Rafraîchir" title="Rafraîchir">
          <RefreshCw size={18} />
        </button>
        {user ? (
          <button className="user-button" type="button" onClick={onLogout} title="Se déconnecter">
            <span>{user.display_name}</span>
            <LogOut size={16} aria-hidden="true" />
            <span className="sr-only">Se déconnecter</span>
          </button>
        ) : (
          <Link className="user-button" to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`}>
            <LogIn size={16} aria-hidden="true" />
            <span>Connexion</span>
          </Link>
        )}
      </div>
    </header>
  );
}
