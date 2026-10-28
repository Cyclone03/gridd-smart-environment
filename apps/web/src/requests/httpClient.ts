/**
 * Client HTTP unique de l'application.
 *
 * Responsabilités : URL de base, en-têtes communs, authentification par
 * jeton, délai d'expiration, sérialisation JSON et traduction homogène des
 * erreurs en `ApiError`. Les composants et les vues n'appellent jamais
 * `fetch` directement : ils passent par les services (src/services).
 */
import { REQUEST_TIMEOUT_MS } from "../constants/app";
import { buildApiUrl } from "./config";

export type QueryValue = string | number | boolean | Date | null | undefined;

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  query?: Record<string, QueryValue>;
  body?: unknown;
  signal?: AbortSignal;
  timeoutMs?: number;
}

/** Erreur normalisée renvoyée par toutes les requêtes. */
export class ApiError extends Error {
  readonly status: number;
  /** Erreurs par champ renvoyées par l'API (format `{ errors: { champ: [..] } }`). */
  readonly fieldErrors: Record<string, string>;
  readonly kind: "http" | "network" | "timeout" | "aborted";

  constructor(
    message: string,
    {
      status = 0,
      fieldErrors = {},
      kind = "http",
    }: { status?: number; fieldErrors?: Record<string, string>; kind?: ApiError["kind"] } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
    this.kind = kind;
  }
}

export function isAbortError(error: unknown): boolean {
  return error instanceof ApiError && error.kind === "aborted";
}

/** Message lisible pour n'importe quelle erreur. */
export function errorMessage(error: unknown, fallback = "Une erreur inattendue est survenue."): string {
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

type TokenProvider = () => string | null;
type UnauthorizedHandler = () => void;

let tokenProvider: TokenProvider = () => null;
let unauthorizedHandler: UnauthorizedHandler = () => undefined;

/** Branché par le store d'authentification. */
export function configureAuth(provider: TokenProvider, onUnauthorized: UnauthorizedHandler) {
  tokenProvider = provider;
  unauthorizedHandler = onUnauthorized;
}

function serializeQuery(query?: Record<string, QueryValue>): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, value instanceof Date ? value.toISOString() : String(value));
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

function flattenFieldErrors(errors: unknown): Record<string, string> {
  if (!errors || typeof errors !== "object") return {};
  const result: Record<string, string> = {};
  for (const [field, messages] of Object.entries(errors as Record<string, unknown>)) {
    if (Array.isArray(messages)) result[field] = messages.map(String).join(" ");
    else if (messages != null) result[field] = String(messages);
  }
  return result;
}

const STATUS_MESSAGES: Record<number, string> = {
  401: "Authentification requise.",
  403: "Vous n'avez pas les droits nécessaires pour cette action.",
  404: "Ressource introuvable.",
  429: "Trop de tentatives. Réessayez dans un instant.",
};

async function toApiError(response: Response): Promise<ApiError> {
  let detail = "";
  let fieldErrors: Record<string, string> = {};
  try {
    const body = (await response.json()) as { detail?: unknown; errors?: unknown };
    if (body && typeof body.detail === "string") detail = body.detail;
    fieldErrors = flattenFieldErrors(body?.errors);
  } catch {
    // Corps non JSON (proxy, page d'erreur HTML) : message générique.
  }
  const message =
    detail ||
    STATUS_MESSAGES[response.status] ||
    (response.status >= 500
      ? "Le serveur GRIDD a rencontré une erreur. Réessayez plus tard."
      : `La requête a échoué (${response.status}).`);
  return new ApiError(message, { status: response.status, fieldErrors });
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", query, body, signal, timeoutMs = REQUEST_TIMEOUT_MS } = options;
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const forwardAbort = () => controller.abort();
  signal?.addEventListener("abort", forwardAbort);

  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = tokenProvider();
  if (token) headers.Authorization = `Token ${token}`;

  let response: Response;
  try {
    response = await fetch(buildApiUrl(path) + serializeQuery(query), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (error) {
    if (timedOut) throw new ApiError("Le serveur GRIDD ne répond pas (délai dépassé).", { kind: "timeout" });
    if (signal?.aborted) throw new ApiError("Requête annulée.", { kind: "aborted" });
    throw new ApiError("Impossible de joindre l'API GRIDD. Vérifiez la connexion réseau.", {
      kind: "network",
      fieldErrors: {},
      status: 0,
    });
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", forwardAbort);
  }

  if (!response.ok) {
    const error = await toApiError(response);
    if (response.status === 401 && token) unauthorizedHandler();
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
