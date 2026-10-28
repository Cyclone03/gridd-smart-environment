import type { FieldErrors } from "../types/common";

export interface AlarmRulePermissions {
  add: boolean;
  change: boolean;
  delete: boolean;
}

/** Utilisateur connecté. Contrat : GET /api/auth/me/. */
export interface AuthUser {
  username: string;
  display_name: string;
  is_staff: boolean;
  permissions: { alarm_rules: AlarmRulePermissions };
}

/** Réponse de POST /api/auth/token/. */
export interface LoginResponse {
  token: string;
  expires_at: string;
  user: AuthUser;
}

export interface Credentials {
  username: string;
  password: string;
}

export function validateCredentials(values: Credentials): FieldErrors<keyof Credentials> {
  const errors: FieldErrors<keyof Credentials> = {};
  if (!values.username.trim()) errors.username = "L'identifiant est obligatoire.";
  if (!values.password) errors.password = "Le mot de passe est obligatoire.";
  return errors;
}

/** Permission demandée par une route (voir routes/index.tsx). */
export type Permission = `alarm_rules.${keyof AlarmRulePermissions}`;

export function hasPermission(user: AuthUser | null, permission: Permission): boolean {
  if (!user) return false;
  const [, action] = permission.split(".") as ["alarm_rules", keyof AlarmRulePermissions];
  return Boolean(user.permissions?.alarm_rules?.[action]);
}
