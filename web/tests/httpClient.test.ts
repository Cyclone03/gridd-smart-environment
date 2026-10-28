import { describe, expect, it, vi } from "vitest";
import { getApiBaseUrl, getWsBaseUrl } from "../src/requests/config";
import { ApiError, configureAuth, request } from "../src/requests/httpClient";
import { mockApi } from "./helpers";

describe("configuration de l'API", () => {
  it("utilise la configuration d'exécution en priorité", () => {
    window.__GRIDD_CONFIG__ = { API_URL: "https://api.example.org/" };
    expect(getApiBaseUrl()).toBe("https://api.example.org");
    expect(getWsBaseUrl()).toBe("wss://api.example.org");
    window.__GRIDD_CONFIG__ = { API_URL: "https://api.example.org", WS_URL: "wss://ws.example.org" };
    expect(getWsBaseUrl()).toBe("wss://ws.example.org");
  });

  it("utilise la même origine par défaut", () => {
    expect(getApiBaseUrl()).toBe("");
    expect(getWsBaseUrl()).toBe(`ws://${window.location.host}`);
  });
});

describe("request", () => {
  it("préfixe l'URL, sérialise la requête et ajoute le jeton", async () => {
    window.__GRIDD_CONFIG__ = { API_URL: "https://api.example.org" };
    const { fetchMock, requests } = mockApi(() => ({ body: { ok: true } }));
    configureAuth(
      () => "abc",
      () => undefined,
    );
    const start = new Date("2026-10-27T12:00:00Z");

    await request("/api/x/", { method: "POST", query: { start, empty: "", skip: undefined, n: 3 }, body: { a: 1 } });

    expect(String(fetchMock.mock.calls[0][0])).toBe(
      "https://api.example.org/api/x/?start=2026-10-27T12%3A00%3A00.000Z&n=3",
    );
    expect(requests[0].headers).toMatchObject({ Authorization: "Token abc", "Content-Type": "application/json" });
    expect(requests[0].body).toEqual({ a: 1 });
    configureAuth(
      () => null,
      () => undefined,
    );
  });

  it("normalise les erreurs de validation de l'API", async () => {
    mockApi(() => ({
      status: 400,
      body: { detail: "Certaines données sont invalides.", errors: { threshold: ["Trop haut.", "Vraiment."] } },
    }));
    const error = await request("/api/x/").catch((reason: unknown) => reason);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(400);
    expect((error as ApiError).message).toBe("Certaines données sont invalides.");
    expect((error as ApiError).fieldErrors).toEqual({ threshold: "Trop haut. Vraiment." });
  });

  it("donne un message explicite pour les erreurs réseau et serveur", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(request("/api/x/")).rejects.toMatchObject({ kind: "network" });
    mockApi(() => ({ status: 500, body: {} }));
    await expect(request("/api/x/")).rejects.toThrow(/serveur GRIDD/);
  });

  it("déconnecte l'utilisateur sur 401 lorsqu'un jeton était envoyé", async () => {
    const onUnauthorized = vi.fn();
    configureAuth(() => "expired", onUnauthorized);
    mockApi(() => ({ status: 401, body: { detail: "Session expirée." } }));
    await expect(request("/api/x/")).rejects.toThrow("Session expirée.");
    expect(onUnauthorized).toHaveBeenCalledOnce();
    configureAuth(
      () => null,
      () => undefined,
    );
  });

  it("interrompt une requête trop longue", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init: RequestInit) =>
          new Promise((_resolve, reject) =>
            init.signal!.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError"))),
          ),
      ),
    );
    await expect(request("/api/x/", { timeoutMs: 10 })).rejects.toMatchObject({ kind: "timeout" });
  });
});
