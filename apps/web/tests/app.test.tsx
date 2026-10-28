import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { dashboardApi, history, manager, renderApp, rule } from "./helpers";

describe("routes et vues principales", () => {
  it("affiche la vue d'ensemble avec les données de l'API", async () => {
    dashboardApi();
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "État environnemental du laboratoire" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("22,4 °C")).toBeInTheDocument());
    expect(screen.getByText("Espaces suivis").nextSibling).toHaveTextContent("2");
    expect(document.title).toBe("Vue d'ensemble · GRIDD");
  });

  it("affiche les espaces avec les seules mesures de leurs capteurs", async () => {
    dashboardApi();
    renderApp("/spaces");
    const card = (await screen.findByRole("heading", { name: "Salle de réunion" })).closest("article")!;
    expect(within(card).getByText("Température")).toBeInTheDocument();
    expect(within(card).queryByText("Présence")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "GRIDD" })).toBeInTheDocument();
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

  it("redirige vers la connexion pour une route protégée", async () => {
    dashboardApi();
    const { router } = renderApp("/alarms/rules/new");
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
    expect(router.state.location.search).toBe("?next=%2Falarms%2Frules%2Fnew");
  });
});

describe("analyse historique et période d'observation", () => {
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
    await user.click(screen.getByRole("button", { name: /Appliquer/ }));

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
  it("permet la consultation sans compte et masque les actions", async () => {
    dashboardApi((request) => (request.path === "/api/alarm-rules/" ? { body: [rule()] } : undefined));
    renderApp("/alarms/rules");
    expect(await screen.findByText("Trop chaud")).toBeInTheDocument();
    expect(screen.getByText("> 28 °C")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Désactiver/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Se connecter pour modifier" })).toBeInTheDocument();
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
    const { requests } = dashboardApi(
      (request) => {
        if (request.path === "/api/alarm-rules/" && request.method === "POST") {
          rules = [...rules, created];
          return { status: 201, body: created };
        }
        if (request.path === "/api/alarm-rules/") return { body: rules };
        return undefined;
      },
      { user: manager },
    );
    const user = userEvent.setup();
    const { router } = renderApp("/alarms/rules/new", { token: "jeton" });

    await user.type(await screen.findByLabelText(/Nom de la règle/), "Capacité");
    await user.selectOptions(screen.getByLabelText(/Paramètre surveillé/), "occupancy");
    await user.selectOptions(screen.getByLabelText(/^Condition/), "gt");
    await user.type(screen.getByLabelText(/^Seuil/), "30");
    await user.click(screen.getByRole("button", { name: /Créer la règle/ }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/alarms/rules"));
    const post = requests.find((item) => item.method === "POST")!;
    expect(post.headers.Authorization).toBe("Token jeton");
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
    const { requests } = dashboardApi(
      (request) => {
        if (request.path === "/api/alarm-rules/7/" && request.method === "PATCH") {
          current = { ...current, ...(request.body as object) };
          return { body: current };
        }
        if (request.path === "/api/alarm-rules/7/" && request.method === "DELETE") return { status: 204 };
        if (request.path === "/api/alarm-rules/7/") return { body: current };
        if (request.path === "/api/alarm-rules/") return { body: [current] };
        return undefined;
      },
      { user: manager },
    );
    const user = userEvent.setup();
    const { router } = renderApp("/alarms/rules/7/edit", { token: "jeton" });

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
    dashboardApi(
      (request) =>
        request.path === "/api/alarm-rules/" && request.method === "POST"
          ? {
              status: 400,
              body: { detail: "Certaines données sont invalides.", errors: { name: ["Nom déjà utilisé."] } },
            }
          : undefined,
      { user: manager },
    );
    const user = userEvent.setup();
    renderApp("/alarms/rules/new", { token: "jeton" });
    await user.type(await screen.findByLabelText(/Nom de la règle/), "Doublon");
    await user.selectOptions(screen.getByLabelText(/Paramètre surveillé/), "temperature");
    await user.selectOptions(screen.getByLabelText(/^Condition/), "gt");
    await user.type(screen.getByLabelText(/^Seuil/), "30");
    await user.click(screen.getByRole("button", { name: /Créer la règle/ }));
    expect(await screen.findByText("Nom déjà utilisé.")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Certaines données sont invalides.");
  });

  it("refuse l'accès à un compte sans droits", async () => {
    dashboardApi(undefined, {
      user: { ...manager, permissions: { alarm_rules: { add: false, change: false, delete: false } } },
    });
    renderApp("/alarms/rules/new", { token: "jeton" });
    expect(await screen.findByText(/Accès refusé/)).toBeInTheDocument();
  });
});

describe("connexion", () => {
  it("connecte l'utilisateur et le renvoie vers la page demandée", async () => {
    const { requests } = dashboardApi((request) =>
      request.path === "/api/auth/token/"
        ? { body: { token: "nouveau", expires_at: "2026-10-28T00:00:00Z", user: manager } }
        : request.path === "/api/alarm-rules/"
          ? { body: [] }
          : undefined,
    );
    const user = userEvent.setup();
    const { router } = renderApp("/login?next=%2Falarms%2Frules");
    await user.type(await screen.findByLabelText("Identifiant"), "gestion");
    await user.type(screen.getByLabelText("Mot de passe"), "secret");
    await user.click(screen.getByRole("button", { name: /Se connecter/ }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/alarms/rules"));
    expect(requests.find((item) => item.path === "/api/auth/token/")!.body).toEqual({
      username: "gestion",
      password: "secret",
    });
    expect(window.localStorage.getItem("gridd-auth-token")).toBe("nouveau");
    expect(await screen.findByRole("link", { name: /Nouvelle règle/ })).toBeInTheDocument();
  });

  it("refuse une redirection externe après connexion", async () => {
    dashboardApi((request) =>
      request.path === "/api/auth/token/" ? { body: { token: "t", expires_at: "", user: manager } } : undefined,
    );
    const user = userEvent.setup();
    const { router } = renderApp("/login?next=%2F%2Fevil.example");
    await user.type(await screen.findByLabelText("Identifiant"), "gestion");
    await user.type(screen.getByLabelText("Mot de passe"), "secret");
    await user.click(screen.getByRole("button", { name: /Se connecter/ }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
  });
});
