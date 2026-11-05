import { useState } from "react";
import { ApiError, errorMessage } from "../requests/httpClient";
import { useAsyncData } from "./useAsyncData";

/**
 * Chargement et modification des paramètres d'une zone (plages de confort,
 * modèle énergétique). `version` change après chaque enregistrement : il sert
 * de clé au formulaire pour repartir des valeurs enregistrées.
 */
export function useProfileEditor<T, V>(
  zoneCode: string | null,
  {
    load,
    save,
    reset,
    onSaved,
  }: {
    load: (zoneCode: string, signal: AbortSignal) => Promise<T>;
    save: (zoneCode: string, values: V) => Promise<T>;
    reset: (zoneCode: string) => Promise<T>;
    onSaved?: () => void;
  },
) {
  const current = useAsyncData(zoneCode ? (signal) => load(zoneCode, signal) : null, [zoneCode]);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<{ message: string; fields: Record<string, string> } | null>(null);
  const [version, setVersion] = useState(0);

  const run = async (action: () => Promise<T>) => {
    setSubmitting(true);
    setServerError(null);
    try {
      await action();
      current.reload();
      setVersion((value) => value + 1);
      onSaved?.();
    } catch (error) {
      setServerError({
        message: errorMessage(error, "Enregistrement impossible."),
        fields: error instanceof ApiError ? error.fieldErrors : {},
      });
    } finally {
      setSubmitting(false);
    }
  };

  return {
    ...current,
    version,
    submitting,
    serverError,
    save: (values: V) => (zoneCode ? run(() => save(zoneCode, values)) : undefined),
    reset: () => (zoneCode ? run(() => reset(zoneCode)) : undefined),
  };
}
