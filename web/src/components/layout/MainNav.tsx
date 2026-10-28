import { NavLink } from "react-router";
import { navigationRoutes } from "../../routes/definitions";

/** Navigation principale, construite à partir de la table des routes. */
export function MainNav({ unreadAlerts }: { unreadAlerts: number }) {
  return (
    <nav className="top-nav" aria-label="Navigation principale">
      {navigationRoutes().map((route) => (
        <NavLink key={route.name} to={route.path} end={route.path === "/"}>
          {route.meta.navLabel}
          {route.name === "alerts" && unreadAlerts > 0 && (
            <span className="nav-badge" aria-label={`${unreadAlerts} alertes non consultées`}>
              +{unreadAlerts}
            </span>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
