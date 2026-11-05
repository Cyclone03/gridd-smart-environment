// @vitest-environment node
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import type { AddressInfo } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createGriddServer, renderEnvScript } from "../server/app";

let baseUrl = "";
let close: () => void;

beforeAll(async () => {
  const dir = mkdtempSync(path.join(tmpdir(), "gridd-web-"));
  mkdirSync(path.join(dir, "assets"));
  writeFileSync(path.join(dir, "index.html"), "<!doctype html><div id=root></div>");
  writeFileSync(path.join(dir, "assets", "app-123.js"), "console.log(1)");
  const server = createGriddServer({
    staticDir: dir,
    env: { GRIDD_API_URL: "https://api.example.org", DJANGO_SECRET_KEY: "ne-doit-pas-fuiter" },
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  baseUrl = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  close = () => server.close();
});

afterAll(() => close());

describe("serveur de production du frontend", () => {
  it("expose uniquement la configuration publique dans /env.js", async () => {
    const response = await fetch(`${baseUrl}/env.js`);
    const body = await response.text();
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(body).toContain('"API_URL":"https://api.example.org"');
    expect(body).not.toContain("ne-doit-pas-fuiter");
  });

  it("échappe les valeurs injectées", () => {
    expect(renderEnvScript({ API_URL: "</script><script>alert(1)" })).not.toContain("</script>");
  });

  it("répond au contrôle de santé", async () => {
    const response = await fetch(`${baseUrl}/healthz`);
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: "ok" });
  });

  it("sert index.html pour les routes de l'application", async () => {
    const response = await fetch(`${baseUrl}/alarms/rules`);
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("text/html");
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
  });

  it("met en cache les fichiers compilés et renvoie 404 pour un fichier absent", async () => {
    const asset = await fetch(`${baseUrl}/assets/app-123.js`);
    expect(asset.headers.get("cache-control")).toContain("immutable");
    expect((await fetch(`${baseUrl}/assets/absent.js`)).status).toBe(404);
  });

  it("refuse les méthodes d'écriture et la traversée de répertoires", async () => {
    expect((await fetch(`${baseUrl}/`, { method: "POST" })).status).toBe(405);
    const traversal = await fetch(`${baseUrl}/..%2f..%2fetc%2fpasswd`);
    expect(await traversal.text()).not.toContain("root:");
  });
});
