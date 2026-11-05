import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { ComfortHistory } from "../src/resources/comfort";
import type { EnergySeries } from "../src/resources/energy";
import { comfort, comfortProfile, dashboardApi, energyProfile, renderApp } from "./helpers";

const comfortHistory: ComfortHistory = {
  zone_code: "meeting-room",
  start: "2026-10-27T00:00:00-04:00",
  end: "2026-10-27T12:00:00-04:00",
  bucket_minutes: 5,
  profile: comfortProfile,
  points: [
    {
      time: "2026-10-27T08:00:00-04:00",
      score: 90,
      temperature: 23,
      humidity: 45,
      comfortable: 3,
      acceptable: 1,
      uncomfortable: 0,
    },
  ],
  summary: { count: 4, average_score: 90, comfortable_ratio: 0.75, acceptable_ratio: 0.25, uncomfortable_ratio: 0 },
};

const energySeries: EnergySeries = {
  zone_code: "meeting-room",
  start: "2026-10-27T00:00:00-04:00",
  end: "2026-10-27T12:00:00-04:00",
  bucket_minutes: 15,
  points: [
    {
      time: "2026-10-27T08:00:00-04:00",
      lighting_kwh: 0.1,
      equipment_kwh: 0.2,
      heating_kwh: 0.05,
      cooling_kwh: 0,
      total_kwh: 0.35,
    },
  ],
  total: {
    lighting_kwh: 0.1,
    equipment_kwh: 0.2,
    heating_kwh: 0.05,
    cooling_kwh: 0,
    total_kwh: 0.35,
    covered_hours: 0.25,
    average_power_w: 1400,
  },
};

describe("vue d'ensemble", () => {
  it("affiche le confort et l'énergie estimée fournis par le backend", async () => {
    dashboardApi();
    renderApp("/");
    expect(await screen.findByText("0/1 confortables")).toBeInTheDocument();
    expect(screen.getByText("score moyen 83/100")).toBeInTheDocument();
    expect(await screen.findByText("14,4 kWh")).toBeInTheDocument();
  });
});

describe("confort thermique", () => {
  it("affiche le confort actuel, l'historique et enregistre des plages personnalisées", async () => {
    const { requests } = dashboardApi((request) => {
      if (request.path === "/api/comfort/zones/meeting-room/history/") return { body: comfortHistory };
      if (request.path === "/api/comfort/profiles/meeting-room/" && request.method === "PATCH")
        return {
          body: { ...comfort[0], customized: true, profile: { ...comfortProfile, ...(request.body as object) } },
        };
      if (request.path === "/api/comfort/profiles/meeting-room/") return { body: { ...comfort[0], assessment: null } };
      return undefined;
    });
    const user = userEvent.setup();
    renderApp("/comfort?zone=meeting-room&period=6h");

    const card = (await screen.findByRole("heading", { name: "Salle de réunion", level: 3 })).closest("button")!;
    expect(within(card).getByText("Acceptable")).toBeInTheDocument();
    expect(within(card).getByText(/Un peu chaud/)).toBeInTheDocument();
    expect(await screen.findByText("75 %")).toBeInTheDocument();

    const minimum = await screen.findByLabelText("Température minimale");
    await user.clear(minimum);
    await user.type(minimum, "26");
    await user.click(screen.getByRole("button", { name: /Enregistrer/ }));
    expect(screen.getByText(/maximale doit être supérieure/)).toBeInTheDocument();
    expect(requests.some((item) => item.method === "PATCH")).toBe(false);

    await user.clear(minimum);
    await user.type(minimum, "19,5");
    await user.click(screen.getByRole("button", { name: /Enregistrer/ }));
    await waitFor(() =>
      expect(requests.find((item) => item.method === "PATCH")?.body).toMatchObject({ temperature_min: 19.5 }),
    );
  });
});

describe("énergie", () => {
  it("affiche le bilan, le détail d'un espace et rétablit ses paramètres par défaut", async () => {
    const { requests } = dashboardApi((request) => {
      if (request.path === "/api/energy/zones/meeting-room/series/") return { body: energySeries };
      if (request.path === "/api/energy/profiles/meeting-room/" && request.method === "DELETE")
        return { body: energyProfile() };
      if (request.path === "/api/energy/profiles/meeting-room/") return { body: energyProfile({ customized: true }) };
      return undefined;
    });
    const user = userEvent.setup();
    renderApp("/energy?period=24h");

    expect(await screen.findByRole("heading", { name: "Consommation énergétique estimée" })).toBeInTheDocument();
    const table = await screen.findByRole("table");
    expect(within(table).getByRole("button", { name: "Salle de réunion" })).toHaveAttribute("aria-pressed", "true");
    expect(within(table).getByText("paramètres personnalisés")).toBeInTheDocument();
    await waitFor(() =>
      expect(requests.some((item) => item.path === "/api/energy/zones/meeting-room/series/")).toBe(true),
    );

    expect(await screen.findByLabelText("Surface")).toHaveValue("30");
    await user.click(screen.getByRole("button", { name: /Valeurs par défaut/ }));
    await waitFor(() => expect(requests.some((item) => item.method === "DELETE")).toBe(true));
  });
});
