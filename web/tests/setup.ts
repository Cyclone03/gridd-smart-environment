import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Recharts (ResponsiveContainer) observe la taille de son conteneur.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);

afterEach(() => {
  // Les tests du serveur Node s'exécutent sans DOM.
  if (typeof window === "undefined") return;
  cleanup();
  window.localStorage.clear();
  delete window.__GRIDD_CONFIG__;
  vi.unstubAllGlobals();
  vi.stubGlobal("ResizeObserver", ResizeObserverStub);
});
