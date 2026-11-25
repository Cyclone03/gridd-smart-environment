import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { REALTIME_RECONNECT_MS } from "../src/constants/app";
import { alert, climatePrediction, dashboardApi, history, observations, renderApp, rule, weatherSnapshot, zones } from "./helpers";

describe("routes et vues principales", () => {
  it("affiche la vue d'ensemble avec les données de l'API", async () => {
    dashboardApi();
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "État environnemental du laboratoire" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText("22,4 °C").length).toBeGreaterThan(0));
    expect(screen.getByText("Espaces suivis").nextSibling).toHaveTextContent("2");
    // Occupation du laboratoire : 6 personnes sur une capacité de 30.
    expect(screen.getByText("Occupation du laboratoire").nextSibling).toHaveTextContent("6 pers.");
    expect(screen.getByText("20 % de la capacité")).toBeInTheDocument();
    expect(screen.queryByText("Confort thermique")).not.toBeInTheDocument();
    expect(screen.queryByText("Énergie estimée (24 h)")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Confort" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Énergie" })).not.toBeInTheDocument();
    expect(document.title).toBe("Vue d'ensemble · GRIDD");
  });

  it("affiche les espaces avec les seules mesures de leurs capteurs", async () => {
    dashboardApi();
    renderApp("/spaces");
    const card = (await screen.findByRole("heading", { name: "Salle de réunion" })).closest("article")!;
    expect(within(card).getByText("Température")).toBeInTheDocument();
    expect(within(card).queryByText("Occupation")).not.toBeInTheDocument();
    const lab = screen.getByRole("heading", { name: "Laboratoire GRIDD" }).closest("article")!;
    expect(within(lab).getByText("Occupation")).toBeInTheDocument();
    expect(within(lab).getByText("6")).toBeInTheDocument();
    // Pas de modèle IA pour le laboratoire entier : pas de prévision intérieure.
    expect(within(lab).queryByText("Prévision intérieure")).not.toBeInTheDocument();
  });

  it("affiche météo extérieure et prévision de l'espace sans météo H+1", async () => {
    dashboardApi((request) =>
      request.path === "/api/weather/latest/" ? { body: weatherSnapshot() } : undefined,
    );
    renderApp("/spaces");
    const card = (await screen.findByRole("heading", { name: "Salle de réunion" })).closest("article")!;
    expect(await within(card).findByRole("region", { name: "Météo extérieure" })).toBeInTheDocument();
    expect(within(card).getByText("Température actuelle")).toBeInTheDocument();
    expect(within(card).getByText("Humidité actuelle")).toBeInTheDocument();
    expect(within(card).getByText("19,2 °C")).toBeInTheDocument();
    expect(within(card).getByText("55,4 %")).toBeInTheDocument();
    expect(within(card).queryByText(/Open-Meteo|Référence météo H\+1/)).not.toBeInTheDocument();
    expect(within(card).getByText("Prévision intérieure")).toBeInTheDocument();
    expect(within(card).getByText("Température prévue")).toBeInTheDocument();
    expect(within(card).getByText("Humidité prévue")).toBeInTheDocument();
    expect(within(card).getAllByText("Indisponible").length).toBeGreaterThan(0);
  });

  it("affiche l'occupation dans tout espace équipé d'un compteur", async () => {
    const zone = { ...zones[0], metrics: [...zones[0].metrics, "occupancy" as const] };
    dashboardApi(undefined, { zones: [zone] });
    renderApp("/spaces");
    const card = (await screen.findByRole("heading", { name: "Salle de réunion" })).closest("article")!;
    expect(within(card).getByText("Occupation")).toBeInTheDocument();
  });

  it("navigue entre les vues depuis la barre principale", async () => {
    dashboardApi();
    const user = userEvent.setup();
    const { router } = renderApp("/");
    await user.click(await screen.findByRole("link", { name: "Alertes" }));
    expect(router.state.location.pathname).toBe("/alerts");
    expect(await screen.findByText("Aucune alerte active")).toBeInTheDocument();
  });

  it("affiche une page 404 pour une adresse inconnue", async () => {
    dashboardApi();
    renderApp("/inexistant");
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeInTheDocument();
  });

  it("affiche une page 404 pour les anciennes routes confort et énergie", async () => {
    dashboardApi();
    const comfortRoute = renderApp("/comfort");
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeInTheDocument();
    comfortRoute.unmount();

    dashboardApi();
    renderApp("/energy");
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeInTheDocument();
  });

  it("n'expose plus de connexion", async () => {
    dashboardApi();
    renderApp("/login");
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Connexion/ })).not.toBeInTheDocument();
  });
});

describe("données du tableau de bord par WebSocket", () => {
  const DASHBOARD_PATHS = ["/api/zones/", "/api/observations/latest/", "/api/alerts/"];

  it("reçoit les données du tableau de bord par WebSocket et charge les prédictions par REST", async () => {
    const { requests } = dashboardApi(undefined, {
      alerts: { active: [alert()], history: [alert({ id: 2, active: false, resolution: "returned_to_normal" })] },
    });
    const user = userEvent.setup();
    renderApp("/");
    await waitFor(() => expect(screen.getAllByText("22,4 °C").length).toBeGreaterThan(0));
    await user.click(screen.getByRole("link", { name: /Alertes/ }));
    expect(await screen.findByText("Retour à la normale")).toBeInTheDocument();
    expect(requests.filter((request) => DASHBOARD_PATHS.includes(request.path))).toEqual([]);
    expect(requests.filter((request) => request.path === "/api/climate-predictions/latest/")).toHaveLength(1);
  });

  it("applique les alertes et les mesures poussées par le serveur", async () => {
    const { realtime, requests } = dashboardApi();
    renderApp("/alerts");
    expect(await screen.findByText("Aucune alerte active")).toBeInTheDocument();

    realtime.push({ event: "alerts.changed", data: { active: [alert()], history: [] } });
    expect(await screen.findByText("Température trop élevée")).toBeInTheDocument();

    realtime.push({
      event: "observation.created",
      data: { ...realtime.state.latest[0], id: 99, value: 24.8, observed_at: new Date().toISOString() },
    });

    await userEvent.setup().click(screen.getByRole("link", { name: /Vue d’ensemble|Vue d'ensemble/ }));
    await waitFor(() => expect(screen.getAllByText("24,8 °C").length).toBeGreaterThan(0));
    expect(requests.filter((request) => DASHBOARD_PATHS.includes(request.path))).toEqual([]);
  });

  it("met à jour le widget météo via le WebSocket après le chargement", async () => {
    const { realtime } = dashboardApi();
    renderApp("/spaces");
    const card = (await screen.findByRole("heading", { name: "Salle de réunion" })).closest("article")!;
    const weather = within(card).getByRole("region", { name: "Météo extérieure" });
    expect(await within(weather).findByText("Indisponible")).toBeInTheDocument();
    realtime.push({ event: "weather_snapshot.created", data: weatherSnapshot() });
    expect(await within(card).findByText("19,2 °C")).toBeInTheDocument();
    expect(within(card).getByText("55,4 %")).toBeInTheDocument();
    expect(within(card).queryByText("20,1 °C")).not.toBeInTheDocument();
  });

  it("le bouton Rafraîchir redemande l'instantané par le WebSocket", async () => {
    const { realtime, requests } = dashboardApi();
    const user = userEvent.setup();
    renderApp("/");
    await screen.findAllByText("22,4 °C");
    await user.click(screen.getByRole("button", { name: "Rafraîchir" }));
    expect(realtime.received).toContainEqual({ action: "snapshot" });
    await waitFor(() =>
      expect(requests.filter((request) => request.path === "/api/climate-predictions/latest/")).toHaveLength(2),
    );
  });

  it("affiche mesures réelles et prédictions séparément, puis applique la mise à jour de la zone", async () => {
    const prediction = climatePrediction();
    const humidity = {
      ...observations[0],
      id: 12,
      type: "humidity" as const,
      value: 45.2,
      unit: "%",
    };
    const otherZone = { ...zones[0], id: 3, name: "Bureau des professeurs", code: "professors-office" };
    let response = [prediction];
    const { realtime } = dashboardApi(
      (request) =>
        request.path === "/api/climate-predictions/latest/"
          ? { body: response }
          : request.path === "/api/weather/latest/"
            ? { body: weatherSnapshot() }
            : undefined,
      { zones: [...zones, otherZone], latest: [...observations, humidity] },
    );
    renderApp("/");
    const section = screen.getByRole("region", { name: "Mesures et prévisions" });
    expect(await within(section).findByText("23,8 °C")).toBeInTheDocument();
    expect(within(section).getByText("22,4 °C")).toBeInTheDocument();
    expect(within(section).getByText("45,2 %")).toBeInTheDocument();
    expect(within(section).getByText("48,2 %")).toBeInTheDocument();
    expect(within(section).getByText("Météo extérieure")).toBeInTheDocument();
    expect(within(section).getByText("19,2 °C")).toBeInTheDocument();
    expect(within(section).getByText("55,4 %")).toBeInTheDocument();
    expect(within(section).getByText(/Prévue pour/)).toBeInTheDocument();

    await userEvent.setup().selectOptions(
      within(section).getByLabelText("Espace pour les prévisions"),
      "professors-office",
    );
    response = [
      climatePrediction({
        prediction_id: 18,
        prediction_event_id: "664c8b13-c0f1-4ca0-9e83-0b427d4e5cf7",
        zone_code: "professors-office",
        predicted_temperature_c: 24.1,
        prediction_mode: "operational",
        model_version: "office-model-v2",
      }),
    ];
    realtime.push({
      event: "climate_prediction.created",
      data: response[0],
    });
    expect(await within(section).findByText("24,1 °C")).toBeInTheDocument();
    expect(within(section).getByRole("heading", { name: "Bureau des professeurs" })).toBeInTheDocument();
  });

  it("signale l'absence et l'expiration sans inventer de valeurs", async () => {
    const { realtime } = dashboardApi((request) =>
      request.path === "/api/climate-predictions/latest/"
        ? {
            body: [
              climatePrediction({
                generated_at: new Date(Date.now() - 120_000).toISOString(),
                target_at: new Date(Date.now() - 60_000).toISOString(),
              }),
            ],
          }
        : undefined,
    );
    renderApp("/");
    const section = screen.getByRole("region", { name: "Mesures et prévisions" });
    expect(await within(section).findByText("Indisponible")).toBeInTheDocument();
    expect(within(section).queryByText("23,8 °C")).not.toBeInTheDocument();
    realtime.push({ event: "climate_prediction.created", data: { zone_code: "meeting-room" } });
    expect(await within(section).findByText("Prévision indisponible.")).toBeInTheDocument();
  });

  it("affiche l'absence de prédictions disponibles", async () => {
    dashboardApi();
    renderApp("/");
    const section = screen.getByRole("region", { name: "Mesures et prévisions" });
    expect(await within(section).findByText("Température prévue")).toBeInTheDocument();
    const predictedTemperature = within(section).getByText("Température prévue").closest("article")!;
    const predictedHumidity = within(section).getByText("Humidité prévue").closest("article")!;
    expect(within(predictedTemperature).getByText("—")).toBeInTheDocument();
    expect(within(predictedHumidity).getByText("—")).toBeInTheDocument();
    expect(within(predictedTemperature).getByText("Indisponible")).toBeInTheDocument();
    expect(within(predictedHumidity).getByText("Indisponible")).toBeInTheDocument();
  });

  it("recharge les prédictions et signale la coupure lors d'une reconnexion WebSocket", async () => {
    let predictions = [climatePrediction()];
    const { requests, realtime } = dashboardApi((request) =>
      request.path === "/api/climate-predictions/latest/" ? { body: predictions } : undefined,
    );
    renderApp("/");
    const section = screen.getByRole("region", { name: "Mesures et prévisions" });
    expect(await within(section).findByText("23,8 °C")).toBeInTheDocument();
    expect(requests.filter((request) => request.path === "/api/climate-predictions/latest/")).toHaveLength(1);

    predictions = [
      climatePrediction({
        prediction_id: 18,
        prediction_event_id: "664c8b13-c0f1-4ca0-9e83-0b427d4e5cf7",
        generated_at: new Date(Date.now() + 60_000).toISOString(),
        predicted_temperature_c: 24.2,
      }),
    ];
    vi.useFakeTimers();
    try {
      await act(async () => {
        realtime.disconnect();
        await Promise.resolve();
      });
      expect(
        within(section).getByText(
          "Connexion interrompue.",
        ),
      ).toBeInTheDocument();
      await act(async () => {
        await vi.advanceTimersByTimeAsync(REALTIME_RECONNECT_MS);
        realtime.openLatest();
      });
    } finally {
      vi.useRealTimers();
    }

    await waitFor(() =>
      expect(requests.filter((request) => request.path === "/api/climate-predictions/latest/")).toHaveLength(2),
    );
    expect(await within(section).findByText("24,2 °C")).toBeInTheDocument();
  });
});

describe("espaces sans données récentes", () => {
  // Capteurs de la salle de réunion muets depuis 5 jours.
  const old = new Date(Date.now() - 5 * 86_400_000).toISOString();
  const silentLatest = observations.map((item) =>
    item.zone_code === "meeting-room" ? { ...item, observed_at: old, received_at: old } : item,
  );

  it("signale l'espace muet au lieu de présenter ses anciennes valeurs comme actuelles", async () => {
    dashboardApi(undefined, { latest: silentLatest });
    renderApp("/spaces");
    expect(await screen.findByText("Pas de données récentes")).toBeInTheDocument();
    expect(screen.getByText(/^Aucune mesure depuis/)).toBeInTheDocument();
  });

  it("exclut les mesures anciennes des moyennes du laboratoire", async () => {
    dashboardApi(undefined, { latest: silentLatest });
    renderApp("/");
    expect(await screen.findAllByText("0/1 espaces à jour")).not.toHaveLength(0);
    expect(screen.queryByText("22,4 °C")).not.toBeInTheDocument();
  });

  it("explique un historique vide par l'arrêt des données", async () => {
    dashboardApi((request) => (request.path.endsWith("/history/") ? { body: history(0) } : undefined), {
      latest: silentLatest,
    });
    renderApp("/history?zone=meeting-room&metric=temperature&period=6h");
    expect(await screen.findByText(/Dernière mesure reçue le .*n’envoie plus de données/)).toBeInTheDocument();
    expect(screen.getByText(/aucune donnée depuis/)).toBeInTheDocument();
  });
});

describe("analyse historique et période d'observation", () => {
  it("met à jour la courbe et les statistiques avec les mesures reçues en direct", async () => {
    const { realtime, requests } = dashboardApi((request) =>
      request.path.endsWith("/history/")
        ? { body: history(24, { type: request.query.get("type") as never }) }
        : undefined,
    );
    renderApp("/history?zone=meeting-room&metric=temperature&period=6h");
    await screen.findByText("Moyennes par créneau de 5 min");
    const stat = () => screen.getByText("Mesures").nextSibling;
    expect(stat()).toHaveTextContent("72");
    const before = requests.length;

    const now = new Date().toISOString();
    realtime.push({
      event: "observation.created",
      data: { ...realtime.state.latest[0], id: 100, value: 30, observed_at: now, received_at: now },
    });
    await waitFor(() => expect(stat()).toHaveTextContent("73"));
    // Lot de mesures (message groupé du serveur).
    const later = new Date(Date.now() + 1000).toISOString();
    realtime.push({
      event: "observations.created",
      data: [101, 102].map((id) => ({
        ...realtime.state.latest[0],
        id,
        value: 31,
        observed_at: later,
        received_at: later,
      })),
    });
    await waitFor(() => expect(stat()).toHaveTextContent("75"));
    // Aucune nouvelle requête : la mesure vient du WebSocket.
    expect(requests.length).toBe(before);
  });

  it("charge la période depuis l'URL et la transmet à l'API", async () => {
    const { requests } = dashboardApi((request) =>
      request.path.endsWith("/history/") ? { body: history(24) } : undefined,
    );
    renderApp("/history?zone=meeting-room&metric=temperature&period=6h");
    expect(await screen.findByText("Moyennes par créneau de 5 min")).toBeInTheDocument();
    const call = requests.find(
      (item) => item.path === "/api/zones/meeting-room/history/" && item.query.get("type") === "temperature",
    )!;
    const span = Date.parse(call.query.get("end")!) - Date.parse(call.query.get("start")!);
    expect(span).toBe(6 * 3_600_000);
    expect(screen.getByText("En hausse")).toBeInTheDocument();
  });

  it("recharge le graphique sans recharger la page quand la période change", async () => {
    const { requests } = dashboardApi((request) =>
      request.path.endsWith("/history/") ? { body: history(24) } : undefined,
    );
    const user = userEvent.setup();
    const { router } = renderApp("/history?zone=meeting-room&metric=temperature&period=6h");
    await screen.findByText("Moyennes par créneau de 5 min");
    const before = requests.length;

    await user.selectOptions(screen.getByLabelText("Période"), "7d");

    await waitFor(() => expect(router.state.location.search).toContain("period=7d"));
    await waitFor(() => {
      const spans = requests
        .slice(before)
        .filter((item) => item.query.get("type") === "temperature")
        .map((item) => Date.parse(item.query.get("end")!) - Date.parse(item.query.get("start")!));
      expect(spans).toContain(7 * 86_400_000);
      // Aucun rechargement intermédiaire avec l'ancienne période.
      expect(spans).not.toContain(6 * 3_600_000);
    });
    expect(screen.getByText("7 derniers jours", { selector: ".chart-heading strong" })).toBeInTheDocument();
  });

  it("gère l'absence de données et les erreurs", async () => {
    let fail = true;
    dashboardApi((request) => {
      if (!request.path.endsWith("/history/")) return undefined;
      if (request.query.get("type") !== "temperature") return { body: history(0) };
      return fail
        ? { status: 400, body: { detail: "La période demandée dépasse la limite de 31 jours." } }
        : { body: history(0) };
    });
    const user = userEvent.setup();
    renderApp("/history?zone=meeting-room&metric=temperature&period=24h");
    // L'erreur s'affiche dans le graphique et dans le panneau de corrélations.
    expect((await screen.findAllByText("La période demandée dépasse la limite de 31 jours.")).length).toBeGreaterThan(
      0,
    );
    fail = false;
    await user.click(screen.getAllByRole("button", { name: "Réessayer" })[0]);
    expect(await screen.findByText("Aucune mesure enregistrée pour cette période.")).toBeInTheDocument();
  });
});

describe("gestion des règles d'alarme", () => {
  it("affiche les règles avec leurs actions, sans compte", async () => {
    dashboardApi((request) => (request.path === "/api/alarm-rules/" ? { body: [rule()] } : undefined));
    renderApp("/alarms/rules");
    expect(await screen.findByText("Trop chaud")).toBeInTheDocument();
    expect(screen.getByText("> 28 °C")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Désactiver/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Nouvelle règle/ })).toBeInTheDocument();
  });

  it("crée une règle puis revient à la liste", async () => {
    const created = rule({
      id: 9,
      name: "Capacité",
      metric: "occupancy",
      threshold: 30,
      condition_label: "> 30 personnes",
    });
    let rules = [rule()];
    const { requests } = dashboardApi((request) => {
      if (request.path === "/api/alarm-rules/" && request.method === "POST") {
        rules = [...rules, created];
        return { status: 201, body: created };
      }
      if (request.path === "/api/alarm-rules/") return { body: rules };
      return undefined;
    });
    const user = userEvent.setup();
    const { router } = renderApp("/alarms/rules/new");

    await user.type(await screen.findByLabelText(/Nom de la règle/), "Capacité");
    await user.selectOptions(screen.getByLabelText(/Paramètre surveillé/), "occupancy");
    await user.selectOptions(screen.getByLabelText(/^Condition/), "gt");
    await user.type(screen.getByLabelText(/^Seuil/), "30");
    await user.click(screen.getByRole("button", { name: /Créer la règle/ }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/alarms/rules"));
    const post = requests.find((item) => item.method === "POST")!;
    expect(post.headers.Authorization).toBeUndefined();
    expect(post.body).toMatchObject({
      name: "Capacité",
      metric: "occupancy",
      operator: "gt",
      threshold: 30,
      zone: null,
    });
    expect(await screen.findByText("Capacité")).toBeInTheDocument();
  });

  it("modifie, désactive et supprime une règle", async () => {
    let current = rule();
    const { requests } = dashboardApi((request) => {
      if (request.path === "/api/alarm-rules/7/" && request.method === "PATCH") {
        current = { ...current, ...(request.body as object) };
        return { body: current };
      }
      if (request.path === "/api/alarm-rules/7/" && request.method === "DELETE") return { status: 204 };
      if (request.path === "/api/alarm-rules/7/") return { body: current };
      if (request.path === "/api/alarm-rules/") return { body: [current] };
      return undefined;
    });
    const user = userEvent.setup();
    const { router } = renderApp("/alarms/rules/7/edit");

    const threshold = await screen.findByLabelText(/^Seuil/);
    expect(threshold).toHaveValue("28");
    await user.clear(threshold);
    await user.type(threshold, "29");
    await user.click(screen.getByRole("button", { name: /Enregistrer les modifications/ }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/alarms/rules"));
    expect(requests.find((item) => item.method === "PATCH")!.body).toMatchObject({ threshold: 29 });

    await user.click(await screen.findByRole("button", { name: /Désactiver/ }));
    await waitFor(() =>
      expect(
        requests.some((item) => item.method === "PATCH" && (item.body as { enabled?: boolean }).enabled === false),
      ).toBe(true),
    );

    await user.click(await screen.findByRole("button", { name: /Supprimer/ }));
    await user.click(screen.getByRole("button", { name: "Oui" }));
    await waitFor(() => expect(requests.some((item) => item.method === "DELETE")).toBe(true));
  });

  it("affiche les erreurs de validation renvoyées par l'API", async () => {
    dashboardApi((request) =>
      request.path === "/api/alarm-rules/" && request.method === "POST"
        ? {
            status: 400,
            body: { detail: "Certaines données sont invalides.", errors: { name: ["Nom déjà utilisé."] } },
          }
        : undefined,
    );
    const user = userEvent.setup();
    renderApp("/alarms/rules/new");
    await user.type(await screen.findByLabelText(/Nom de la règle/), "Doublon");
    await user.selectOptions(screen.getByLabelText(/Paramètre surveillé/), "temperature");
    await user.selectOptions(screen.getByLabelText(/^Condition/), "gt");
    await user.type(screen.getByLabelText(/^Seuil/), "30");
    await user.click(screen.getByRole("button", { name: /Créer la règle/ }));
    expect(await screen.findByText("Nom déjà utilisé.")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Certaines données sont invalides.");
  });
});
