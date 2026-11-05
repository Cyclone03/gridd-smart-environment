import type { EnergyProfileField, EnergyUse } from "../resources/energy";
import type { ProfileFieldMeta } from "../resources/profile";

/** Présentation des usages de l'énergie. */
export const ENERGY_USES: Record<EnergyUse, { label: string; color: string }> = {
  lighting: { label: "Éclairage", color: "#d9a21b" },
  equipment: { label: "Équipements", color: "#7259bd" },
  heating: { label: "Chauffage", color: "#c55d45" },
  cooling: { label: "Climatisation", color: "#2184a7" },
};

export const ENERGY_USE_ORDER: EnergyUse[] = ["lighting", "equipment", "heating", "cooling"];

/** Champs du formulaire des paramètres du modèle (bornes identiques à l'API). */
export const ENERGY_PROFILE_FIELDS: ProfileFieldMeta<EnergyProfileField>[] = [
  { key: "floor_area_m2", label: "Surface", unit: "m²", min: 0, max: 10_000, group: "Espace" },
  {
    key: "default_occupancy",
    label: "Occupation par défaut",
    unit: "pers.",
    min: 0,
    max: 500,
    integer: true,
    hint: "Utilisée quand aucune mesure d'occupation n'est disponible.",
    group: "Espace",
  },
  {
    key: "lighting_w_per_m2",
    label: "Éclairage",
    unit: "W/m²",
    min: 0,
    max: 50,
    hint: "Réduit à 10 % sans occupant.",
    group: "Éclairage et équipements",
  },
  {
    key: "equipment_base_w",
    label: "Équipements fixes",
    unit: "W",
    min: 0,
    max: 1_000_000,
    group: "Éclairage et équipements",
  },
  {
    key: "equipment_w_per_person",
    label: "Équipements par personne",
    unit: "W",
    min: 0,
    max: 5_000,
    group: "Éclairage et équipements",
  },
  {
    key: "envelope_ua_w_per_k",
    label: "Déperditions de l'enveloppe",
    unit: "W/K",
    min: 0,
    max: 100_000,
    hint: "Puissance perdue par degré d'écart avec l'extérieur.",
    group: "Chauffage et climatisation",
  },
  {
    key: "ventilation_l_s_per_person",
    label: "Air neuf par personne",
    unit: "L/s",
    min: 0,
    max: 100,
    group: "Chauffage et climatisation",
  },
  {
    key: "outdoor_temperature_c",
    label: "Température extérieure de référence",
    unit: "°C",
    min: -50,
    max: 50,
    group: "Chauffage et climatisation",
  },
  {
    key: "heating_cop",
    label: "Rendement du chauffage (COP)",
    unit: "",
    min: 0.5,
    max: 10,
    group: "Chauffage et climatisation",
  },
  {
    key: "cooling_cop",
    label: "Rendement de la climatisation (COP)",
    unit: "",
    min: 0.5,
    max: 10,
    group: "Chauffage et climatisation",
  },
];
