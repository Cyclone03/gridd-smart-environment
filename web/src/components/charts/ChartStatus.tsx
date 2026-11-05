import { ErrorMessage, Loading } from "../common/Feedback";

/**
 * Contenu de remplacement d'un graphique : chargement, erreur ou absence de
 * données. Retourne `null` lorsque le graphique peut être affiché.
 */
export function ChartStatus({
  loading,
  error,
  empty,
  onRetry,
  emptyLabel = "Aucune mesure enregistrée pour cette période.",
}: {
  loading: boolean;
  error: string | null;
  empty: boolean;
  onRetry?: () => void;
  emptyLabel?: string;
}) {
  if (error)
    return (
      <div className="chart-empty">
        <ErrorMessage onRetry={onRetry}>{error}</ErrorMessage>
      </div>
    );
  if (loading && empty)
    return (
      <div className="chart-empty">
        <Loading label="Chargement des mesures…" />
      </div>
    );
  if (empty) return <div className="chart-empty">{emptyLabel}</div>;
  return null;
}
