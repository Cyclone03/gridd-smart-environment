import { useCallback } from "react";
import { useSearchParams } from "react-router";

/** Zone sélectionnée dans une vue, synchronisée avec `?zone=` dans l'URL. */
export function useZoneSelection(available: string[]) {
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get("zone");
  const zoneCode = requested && available.includes(requested) ? requested : (available[0] ?? null);

  const select = useCallback(
    (code: string) =>
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          next.set("zone", code);
          return next;
        },
        { replace: true },
      ),
    [setSearchParams],
  );

  return { zoneCode, select };
}
