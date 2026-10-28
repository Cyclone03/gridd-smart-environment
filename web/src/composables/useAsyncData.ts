import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage, isAbortError } from "../requests/httpClient";
import type { AsyncState } from "../types/common";

/**
 * Charge une donnée asynchrone et gère chargement, erreur et annulation.
 *
 * La requête précédente est annulée quand `deps` change ou au démontage, ce
 * qui évite d'afficher le résultat d'une sélection périmée.
 *
 * @param loader fonction recevant un `AbortSignal`, ou `null` pour ne rien charger
 * @param deps   dépendances déclenchant un nouveau chargement
 * @param options.keepPrevious conserve la donnée précédente pendant le rechargement
 */
export function useAsyncData<T>(
  loader: ((signal: AbortSignal) => Promise<T>) | null,
  deps: readonly unknown[],
  { keepPrevious = false }: { keepPrevious?: boolean } = {},
): AsyncState<T> & { reload: () => void } {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: Boolean(loader), error: null });
  const [reloadKey, setReloadKey] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    const load = loaderRef.current;
    if (!load) {
      setState({ data: null, loading: false, error: null });
      return;
    }
    const controller = new AbortController();
    setState((current) => ({ data: keepPrevious ? current.data : null, loading: true, error: null }));
    load(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ data, loading: false, error: null });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isAbortError(error)) return;
        setState((current) => ({
          data: keepPrevious ? current.data : null,
          loading: false,
          error: errorMessage(error, "Chargement impossible."),
        }));
      });
    return () => controller.abort();
  }, [...deps, reloadKey, Boolean(loader)]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);
  return { ...state, reload };
}
