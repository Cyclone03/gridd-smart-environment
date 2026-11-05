import type { ComfortLevel, ComfortProfileField, HumidityStatus, TemperatureStatus } from "../resources/comfort";
import type { ProfileFieldMeta } from "../resources/profile";

/** Présentation des niveaux de confort. */
export const COMFORT_LEVELS: Record<ComfortLevel, { label: string; color: string; className: string }> = {
  comfortable: { label: "Confortable", color: "#0d725f", className: "comfort-comfortable" },
  acceptable: { label: "Acceptable", color: "#c28a1e", className: "comfort-acceptable" },
  uncomfortable: { label: "Inconfortable", color: "#b53e35", className: "comfort-uncomfortable" },
  unknown: { label: "Indéterminé", color: "#8a9692", className: "comfort-unknown" },
};

export const TEMPERATURE_STATUS_LABELS: Record<TemperatureStatus, string> = {
  ok: "Dans la plage",
  cool: "Un peu frais",
  too_cold: "Trop froid",
  warm: "Un peu chaud",
  too_hot: "Trop chaud",
  unknown: "Non mesurée",
};

export const HUMIDITY_STATUS_LABELS: Record<HumidityStatus, string> = {
  ok: "Dans la plage",
  dry: "Un peu sec",
  too_dry: "Trop sec",
  humid: "Un peu humide",
  too_humid: "Trop humide",
  unknown: "Non mesurée",
};

/** Champs du formulaire des plages de confort (bornes identiques à l'API). */
export const COMFORT_PROFILE_FIELDS: ProfileFieldMeta<ComfortProfileField>[] = [
  { key: "temperature_min", label: "Température minimale", unit: "°C", min: -20, max: 60, group: "Température" },
  { key: "temperature_max", label: "Température maximale", unit: "°C", min: -20, max: 60, group: "Température" },
  {
    key: "temperature_tolerance",
    label: "Tolérance",
    unit: "°C",
    min: 0.1,
    max: 20,
    hint: "Écart hors plage encore jugé acceptable.",
    group: "Température",
  },
  { key: "humidity_min", label: "Humidité minimale", unit: "%", min: 0, max: 100, group: "Humidité relative" },
  { key: "humidity_max", label: "Humidité maximale", unit: "%", min: 0, max: 100, group: "Humidité relative" },
  {
    key: "humidity_tolerance",
    label: "Tolérance",
    unit: "%",
    min: 0.1,
    max: 50,
    hint: "Écart hors plage encore jugé acceptable.",
    group: "Humidité relative",
  },
];
