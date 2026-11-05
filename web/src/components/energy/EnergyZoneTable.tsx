import { ENERGY_USE_ORDER, ENERGY_USES } from "../../constants/energy";
import type { ZoneEnergy } from "../../resources/energy";
import { formatEnergy, formatNumber, formatPower, zoneDisplayName } from "../../utils/format";

/** Tableau de l'énergie estimée par espace ; une ligne sélectionne l'espace. */
export function EnergyZoneTable({
  zones,
  selected,
  onSelect,
}: {
  zones: ZoneEnergy[];
  selected: string | null;
  onSelect: (zoneCode: string) => void;
}) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Espace</th>
            <th scope="col">Total</th>
            {ENERGY_USE_ORDER.map((use) => (
              <th scope="col" key={use}>
                {ENERGY_USES[use].label}
              </th>
            ))}
            <th scope="col">Puissance moyenne</th>
            <th scope="col">Durée estimée</th>
          </tr>
        </thead>
        <tbody>
          {zones.map((zone) => (
            <tr key={zone.zone_code} className={selected === zone.zone_code ? "selected" : ""}>
              <th scope="row">
                <button
                  type="button"
                  onClick={() => onSelect(zone.zone_code)}
                  aria-pressed={selected === zone.zone_code}
                >
                  {zoneDisplayName({ code: zone.zone_code, name: zone.zone_name })}
                </button>
                {zone.customized && <small>paramètres personnalisés</small>}
              </th>
              <td>
                <strong>{formatEnergy(zone.total_kwh)}</strong>
              </td>
              {ENERGY_USE_ORDER.map((use) => (
                <td key={use}>{formatEnergy(zone[`${use}_kwh`])}</td>
              ))}
              <td>{formatPower(zone.average_power_w)}</td>
              <td>{zone.covered_hours ? `${formatNumber(zone.covered_hours, 1)} h` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
