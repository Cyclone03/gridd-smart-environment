/** Types transversaux, non liés à une ressource de l'API. */

/** État de la connexion temps réel (WebSocket). */
export type RealtimeStatus = "connecting" | "connected" | "disconnected";

/** État d'une donnée chargée de façon asynchrone. */
export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/** Erreurs de validation par champ, prêtes à afficher. */
export type FieldErrors<Field extends string = string> = Partial<Record<Field, string>>;
