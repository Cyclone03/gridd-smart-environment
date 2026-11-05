/**
 * Ajustements d'affichage des zones.
 *
 * Les zones sont créées automatiquement à partir des messages Kafka : leur nom
 * technique n'est pas toujours présentable. Pour masquer durablement une zone,
 * préférer « active = false » dans l'admin Django ; cette liste conserve le
 * comportement existant de l'interface.
 */
export const ZONE_DISPLAY_NAMES: Record<string, string> = {
  "occupancy-camera": "GRIDD",
};

/** Zones présentes en base mais non affichées. */
export const HIDDEN_ZONE_NAMES = new Set(["Salle du GRIDD"]);

export const ZONE_TYPE_LABELS: Record<string, string> = {
  server_room: "Salle serveur",
  meeting_room: "Salle de réunion",
  office: "Bureau",
  cubicle: "Cubicule",
  open_workspace: "Espace ouvert",
  classroom: "Salle de cours",
  lab: "Laboratoire",
  other: "Espace",
};
