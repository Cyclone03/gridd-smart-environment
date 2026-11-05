/** Convertit « 21,5 » ou « 21.5 » en nombre ; `null` si invalide. */
export function parseDecimal(value: string): number | null {
  const normalized = value.trim().replace(/\s/g, "").replace(",", ".");
  if (!normalized || !/^-?\d+(\.\d+)?$/.test(normalized)) return null;
  return Number(normalized);
}
