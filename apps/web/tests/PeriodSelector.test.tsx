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

  it("applique immédiatement une période prédéfinie", async () => {
    const { onApply, user } = setup();
    await user.selectOptions(screen.getByLabelText("Période"), "7d");
    expect(onApply).toHaveBeenCalledWith({ kind: "preset", preset: "7d" });
  });

  it("valide une plage personnalisée et l'applique quand elle devient valide", async () => {
    const { onApply, user } = setup();
    await user.selectOptions(screen.getByLabelText("Période"), "custom");
    const toLocalInput = (date: Date) =>
      new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
        .toISOString()
        .slice(0, 16);
    const start = new Date(Date.now() - 48 * 60 * 60 * 1_000);
    const end = new Date(Date.now() - 36 * 60 * 60 * 1_000);
    const startValue = toLocalInput(start);
    const endValue = toLocalInput(end);

    fireEvent.change(screen.getByLabelText("Fin"), { target: { value: endValue } });
    expect(onApply).not.toHaveBeenCalled();
    expect(screen.getByText("La fin doit être postérieure au début.")).toBeInTheDocument();
    expect(screen.getByLabelText("Fin")).toHaveAttribute("aria-invalid", "true");

    fireEvent.change(screen.getByLabelText("Début"), { target: { value: startValue } });
    expect(onApply).toHaveBeenCalledWith({
      kind: "custom",
      start: new Date(startValue).toISOString(),
      end: new Date(endValue).toISOString(),
    });
  });

  it("propose l'actualisation", async () => {
    const { onRefresh, user } = setup();
    await user.click(screen.getByRole("button", { name: /Actualiser/ }));
    expect(onRefresh).toHaveBeenCalled();
  });
});
