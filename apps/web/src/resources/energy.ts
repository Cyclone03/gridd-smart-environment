/**
 * Consommation énergétique **estimée** par un modèle paramétrable (aucune
 * mesure de consommation). Contrat : /api/energy/ (docs/api.md).
 */

export type EnergyUse = "lighting" | "equipment" | "heating" | "cooling";

export interface EnergyProfile {
  floor_area_m2: number;
  lighting_w_per_m2: number;
  equipment_base_w: number;
  equipment_w_per_person: number;
  default_occupancy: number;
  envelope_ua_w_per_k: number;
  ventilation_l_s_per_person: number;
  outdoor_temperature_c: number;
  heating_cop: number;
  cooling_cop: number;
}

export type EnergyProfileField = keyof EnergyProfile;

export interface ZoneEnergyProfile {
  zone_code: string;
  zone_name: string;
  zone_type: string;
  customized: boolean;
  profile: EnergyProfile;
}

export interface EnergyTotals {
  lighting_kwh: number;
  equipment_kwh: number;
  heating_kwh: number;
  cooling_kwh: number;
  total_kwh: number;
  /** Durée réellement estimée sur la période (heures). */
  covered_hours: number;
  average_power_w: number | null;
}

export interface ZoneEnergy extends EnergyTotals {
  zone_code: string;
  zone_name: string;
  zone_type: string;
  customized: boolean;
}

/** GET /api/energy/summary/ */
export interface EnergySummary {
  start: string;
  end: string;
  total: EnergyTotals;
  zones: ZoneEnergy[];
}

export interface EnergySeriesPoint {
  time: string;
  lighting_kwh: number;
  equipment_kwh: number;
  heating_kwh: number;
  cooling_kwh: number;
  total_kwh: number;
}

/** GET /api/energy/zones/<code>/series/ */
export interface EnergySeries {
  zone_code: string;
  start: string;
  end: string;
  bucket_minutes: number;
  points: EnergySeriesPoint[];
  total: EnergyTotals;
}

export interface PeriodQuery {
  start: Date;
  end: Date;
}

const ZERO: EnergyTotals = {
  lighting_kwh: 0,
  equipment_kwh: 0,
  heating_kwh: 0,
  cooling_kwh: 0,
  total_kwh: 0,
  covered_hours: 0,
  average_power_w: null,
};

/**
 * Totaux des espaces affichés. La puissance moyenne additionne celle de
 * chaque espace (puissance moyenne de l'ensemble sur la période).
 */
export function sumEnergy(zones: EnergyTotals[]): EnergyTotals {
  return zones.reduce<EnergyTotals>(
    (total, zone) => ({
      lighting_kwh: total.lighting_kwh + zone.lighting_kwh,
      equipment_kwh: total.equipment_kwh + zone.equipment_kwh,
      heating_kwh: total.heating_kwh + zone.heating_kwh,
      cooling_kwh: total.cooling_kwh + zone.cooling_kwh,
      total_kwh: total.total_kwh + zone.total_kwh,
      covered_hours: Math.max(total.covered_hours, zone.covered_hours),
      average_power_w:
        zone.average_power_w == null ? total.average_power_w : (total.average_power_w ?? 0) + zone.average_power_w,
    }),
    ZERO,
  );
}
