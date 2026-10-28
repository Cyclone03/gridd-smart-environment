import { request } from "../requests/httpClient";
import type { AuthUser, Credentials, LoginResponse } from "../resources/auth";

export function login(credentials: Credentials) {
  return request<LoginResponse>("/api/auth/token/", { method: "POST", body: credentials });
}

export function fetchCurrentUser(signal?: AbortSignal) {
  return request<AuthUser>("/api/auth/me/", { signal });
}

export function logout() {
  return request<void>("/api/auth/logout/", { method: "POST" });
}
