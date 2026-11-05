import { parseDecimal } from "../utils/numbers";

/**
 * Paramètres numériques d'un espace (plages de confort, modèle énergétique).
 * Description des champs et validation commune des formulaires.
 */
export interface ProfileFieldMeta<K extends string> {
  key: K;
  label: string;
  unit: string;
  min: number;
  max: number;
  /** Valeur entière attendue (ex. nombre de personnes). */
  integer?: boolean;
  hint?: string;
  /** Regroupement visuel dans le formulaire. */
  group: string;
}

export type ProfileDraft<K extends string> = Record<K, string>;
export type ProfileErrors<K extends string> = Partial<Record<K, string>>;

export function draftFromProfile<K extends string>(profile: Record<K, number>): ProfileDraft<K> {
  return Object.fromEntries(
    Object.entries(profile).map(([key, value]) => [key, String(value).replace(".", ",")]),
  ) as ProfileDraft<K>;
}

/**
 * Valide un brouillon : nombre (virgule acceptée), bornes, entier si demandé,
 * puis contrôles croisés propres au profil (`cross`). Le backend applique les
 * mêmes règles et reste l'autorité.
 */
export function validateProfileDraft<K extends string>(
  fields: ProfileFieldMeta<K>[],
  draft: ProfileDraft<K>,
  cross: (values: Record<K, number>) => ProfileErrors<K> = () => ({}),
): { errors: ProfileErrors<K>; values?: Record<K, number> } {
  const errors: ProfileErrors<K> = {};
  const values = {} as Record<K, number>;
  for (const field of fields) {
    const value = parseDecimal(draft[field.key] ?? "");
    if (value === null) errors[field.key] = "Nombre attendu.";
    else if (value < field.min || value > field.max)
      errors[field.key] = `Entre ${field.min} et ${field.max} ${field.unit}.`.replace(/ \.$/, ".");
    else if (field.integer && !Number.isInteger(value)) errors[field.key] = "Nombre entier attendu.";
    else values[field.key] = value;
  }
  if (Object.keys(errors).length) return { errors };
  const crossErrors = cross(values);
  return Object.keys(crossErrors).length ? { errors: crossErrors } : { errors, values };
}
