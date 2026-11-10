import { Building2, Search } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";
import { PageHeader } from "../components/common/PageHeader";
import { ZoneCard } from "../components/measurements/ZoneCard";
import { LOCALE } from "../constants/app";
import { routePath } from "../routes/definitions";
import { useDashboard } from "../stores/dashboardStore";
import { formatZoneType, zoneDisplayName } from "../utils/format";

export function SpacesView() {
  const { zones, latest, alerts, loading } = useDashboard();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const needle = query.trim().toLocaleLowerCase(LOCALE);
  const filtered = zones.filter((zone) =>
    `${zoneDisplayName(zone)} ${formatZoneType(zone.zone_type)}`.toLocaleLowerCase(LOCALE).includes(needle),
  );

  return (
    <main className="dashboard page-view">
      <PageHeader
        icon={Building2}
        overline="Espaces"
        title="Tous les espaces surveillés"
        description="Dernières mesures reçues, sans remplacer les valeurs absentes."
      />
      <section className="spaces-section">
        <div className="section-bar">
          <div>
            <span className="section-kicker">Toutes les zones</span>
            <h2>Espaces surveillés</h2>
          </div>
          <label className="search-box">
            <Search size={17} aria-hidden="true" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Rechercher un espace"
              aria-label="Rechercher un espace"
            />
          </label>
        </div>
        <div className="zones-grid">
          {loading
            ? Array.from({ length: 6 }, (_, index) => <div className="zone-card skeleton" key={index} />)
            : filtered.map((zone) => (
                <ZoneCard
                  key={zone.code}
                  zone={zone}
                  latest={latest}
                  alertCount={alerts.filter((alert) => alert.zone === zone.id).length}
                  onHistory={() => navigate(`${routePath("history")}?zone=${encodeURIComponent(zone.code)}`)}
                />
              ))}
          {!loading && !filtered.length && <p className="muted-note">Aucun espace ne correspond à la recherche.</p>}
        </div>
      </section>
    </main>
  );
}
