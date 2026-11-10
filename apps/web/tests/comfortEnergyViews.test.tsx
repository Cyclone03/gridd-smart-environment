import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { dashboardApi, renderApp } from "./helpers";

describe("fonctionnalités reportées", () => {
  it("n'affiche ni confort ni énergie dans la vue d'ensemble ou la navigation", async () => {
    dashboardApi();
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "État environnemental du laboratoire" })).toBeInTheDocument();
    expect(screen.queryByText("Confort thermique")).not.toBeInTheDocument();
    expect(screen.queryByText("Énergie estimée (24 h)")).not.toBeInTheDocument();
    expect(screen.queryByText("Indice de confort sonore")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Confort" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Énergie" })).not.toBeInTheDocument();
  });

  it.each(["/comfort", "/energy"])("rend la page introuvable sur %s", async (path) => {
    dashboardApi();
    renderApp(path);
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeInTheDocument();
  });
});
