import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AlarmRuleForm } from "../src/components/forms/AlarmRuleForm";
import { draftFromRule, emptyAlarmRuleDraft } from "../src/resources/alarmRule";
import { metadata, rule, zones } from "./helpers";

function setup(props: Partial<Parameters<typeof AlarmRuleForm>[0]> = {}) {
  const onSubmit = vi.fn();
  render(
    <AlarmRuleForm
      initial={emptyAlarmRuleDraft()}
      metadata={metadata}
      zones={zones}
      submitting={false}
      submitLabel="Créer la règle"
      onSubmit={onSubmit}
      onCancel={() => undefined}
      {...props}
    />,
  );
  return { onSubmit, user: userEvent.setup() };
}

describe("AlarmRuleForm", () => {
  it("bloque l'envoi et signale les champs invalides", async () => {
    const { onSubmit, user } = setup();
    await user.click(screen.getByRole("button", { name: /Créer la règle/ }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText("Le nom est obligatoire.")).toBeInTheDocument();
    expect(screen.getByLabelText(/Nom de la règle/)).toHaveAttribute("aria-invalid", "true");
  });

  it("crée une règle d'intervalle et décrit le comportement attendu", async () => {
    const { onSubmit, user } = setup();
    await user.type(screen.getByLabelText(/Nom de la règle/), "Confort thermique");
    await user.selectOptions(screen.getByLabelText(/Paramètre surveillé/), "temperature");
    await user.selectOptions(screen.getByLabelText(/^Espace/), "meeting-room");
    await user.selectOptions(screen.getByLabelText(/^Condition/), "outside_range");
    await user.type(screen.getByLabelText(/Borne basse/), "18");
    await user.type(screen.getByLabelText(/Borne haute/), "26,5");
    await user.selectOptions(screen.getByLabelText(/Gravité/), "critical");

    expect(screen.getByText(/sort de l’intervalle \[18 ; 26,5\] °C dans « Salle de réunion »/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Créer la règle/ }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "Confort thermique",
        zone: "meeting-room",
        operator: "outside_range",
        threshold: 18,
        threshold_high: 26.5,
        severity: "critical",
      }),
    );
  });

  it("affiche les erreurs renvoyées par l'API", () => {
    setup({
      initial: draftFromRule(rule()),
      serverMessage: "Certaines données sont invalides.",
      serverErrors: { threshold: "Valeur hors des limites physiques du capteur." },
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Certaines données sont invalides.");
    expect(screen.getByText("Valeur hors des limites physiques du capteur.")).toBeInTheDocument();
  });

  it("réinitialise une condition incompatible avec le nouveau paramètre", async () => {
    const limited = {
      ...metadata,
      metrics: [metadata.metrics[0], { ...metadata.metrics[1], operators: ["gt" as const] }],
    };
    const { user } = setup({
      metadata: limited,
      initial: { ...emptyAlarmRuleDraft(), metric: "temperature", operator: "lt" },
    });
    await user.selectOptions(screen.getByLabelText(/Paramètre surveillé/), "occupancy");
    expect(screen.getByLabelText(/^Condition/)).toHaveValue("");
  });
});
