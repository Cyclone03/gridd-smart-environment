import { Leaf, RefreshCw } from "lucide-react";
import { Link } from "react-router";
import type { RealtimeStatus } from "../../types/common";
import { StatusPill } from "../common/StatusPill";
import { MainNav } from "./MainNav";

export function TopBar({
  status,
  unreadAlerts,
  onRefresh,
}: {
  status: RealtimeStatus;
  unreadAlerts: number;
  onRefresh: () => void;
}) {
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
      </div>
    </header>
  );
}
