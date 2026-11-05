import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PeriodSelector } from "../src/components/forms/PeriodSelector";
import type { ObservationPeriod } from "../src/resources/period";
import { resolvePeriod } from "../src/utils/period";

function setup(period: ObservationPeriod = { kind: "preset", preset: "today" }) {
  const onApply = vi.fn();
  const onRefresh = vi.fn();
  render(<PeriodSelector period={period} resolved={resolvePeriod(period)} onApply={onApply} onRefresh={onRefresh} />);
  return { onApply, onRefresh, user: userEvent.setup() };
}

describe("PeriodSelector", () => {
  it("affiche la période appliquée", () => {
    setup({ kind: "preset", preset: "24h" });
    expect(screen.getByText("24 dernières heures", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText(/actualisation automatique/)).toBeInTheDocument();
  });

  it("applique une période prédéfinie avec le bouton", async () => {
    const { onApply, user } = setup();
    await user.selectOptions(screen.getByLabelText("Période"), "7d");
    expect(screen.getByText("Modification non appliquée")).toBeInTheDocument();
    expect(onApply).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: /Appliquer/ }));
    expect(onApply).toHaveBeenCalledWith({ kind: "preset", preset: "7d" });
  });

  it("valide puis applique une plage personnalisée", async () => {
    const { onApply, user } = setup();
    await user.selectOptions(screen.getByLabelText("Période"), "custom");
    fireEvent.change(screen.getByLabelText("Début"), { target: { value: "2026-10-21T10:00" } });
    fireEvent.change(screen.getByLabelText("Fin"), { target: { value: "2026-10-20T10:00" } });
    await user.click(screen.getByRole("button", { name: /Appliquer/ }));
    expect(onApply).not.toHaveBeenCalled();
    expect(screen.getByText("La fin doit être postérieure au début.")).toBeInTheDocument();
    expect(screen.getByLabelText("Fin")).toHaveAttribute("aria-invalid", "true");

    fireEvent.change(screen.getByLabelText("Fin"), { target: { value: "2026-10-22T10:00" } });
    await user.click(screen.getByRole("button", { name: /Appliquer/ }));
    expect(onApply).toHaveBeenCalledWith({
      kind: "custom",
      start: new Date("2026-10-21T10:00").toISOString(),
      end: new Date("2026-10-22T10:00").toISOString(),
    });
  });

  it("propose l'actualisation", async () => {
    const { onRefresh, user } = setup();
    await user.click(screen.getByRole("button", { name: /Actualiser/ }));
    expect(onRefresh).toHaveBeenCalled();
  });
});
