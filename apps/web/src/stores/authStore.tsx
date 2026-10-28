/**
 * État d'authentification partagé.
 *
 * Le jeton est conservé dans le stockage local du navigateur pour survivre à
 * un rechargement ; il expire côté serveur (AUTH_TOKEN_TTL_HOURS). Une
 * réponse 401 sur une requête authentifiée déconnecte l'utilisateur.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { STORAGE_KEYS } from "../constants/app";
import { configureAuth, isAbortError } from "../requests/httpClient";
import { hasPermission, type AuthUser, type Credentials, type Permission } from "../resources/auth";
import * as authService from "../services/authService";
import { readStorage, writeStorage } from "../utils/storage";

interface AuthContextValue {
  user: AuthUser | null;
  /** Vrai tant que la session enregistrée n'a pas été vérifiée. */
  initializing: boolean;
  login: (credentials: Credentials) => Promise<AuthUser>;
  logout: () => Promise<void>;
  can: (permission: Permission) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const tokenRef = useRef<string | null>(readStorage(STORAGE_KEYS.authToken));
  const [user, setUser] = useState<AuthUser | null>(null);
  const [initializing, setInitializing] = useState(Boolean(tokenRef.current));

  const clearSession = useCallback(() => {
    tokenRef.current = null;
    writeStorage(STORAGE_KEYS.authToken, null);
    setUser(null);
  }, []);

  // Branché pendant le premier rendu : les effets des composants enfants
  // (premiers appels API) s'exécutent avant ceux de ce fournisseur.
  const configured = useRef(false);
  if (!configured.current) {
    configureAuth(() => tokenRef.current, clearSession);
    configured.current = true;
  }

  useEffect(() => {
    if (!tokenRef.current) return;
    const controller = new AbortController();
    authService
      .fetchCurrentUser(controller.signal)
      .then(setUser)
      .catch((error: unknown) => {
        if (!isAbortError(error)) clearSession();
      })
      .finally(() => {
        if (!controller.signal.aborted) setInitializing(false);
      });
    return () => controller.abort();
  }, [clearSession]);

  const login = useCallback(async (credentials: Credentials) => {
    const response = await authService.login(credentials);
    tokenRef.current = response.token;
    writeStorage(STORAGE_KEYS.authToken, response.token);
    setUser(response.user);
    return response.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      if (tokenRef.current) await authService.logout();
    } catch {
      // Jeton déjà expiré : la session locale est effacée dans tous les cas.
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, initializing, login, logout, can: (permission) => hasPermission(user, permission) }),
    [user, initializing, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth doit être utilisé dans <AuthProvider>.");
  return context;
}
