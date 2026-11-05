import { describe, expect, it } from "vitest";
import { COMFORT_PROFILE_FIELDS } from "../src/constants/comfort";
import { ENERGY_PROFILE_FIELDS } from "../src/constants/energy";
import { applyComfortUpdate, comfortProfileErrors } from "../src/resources/comfort";
import { sumEnergy } from "../src/resources/energy";
import { draftFromProfile, validateProfileDraft } from "../src/resources/profile";
import { parseRealtimeMessage } from "../src/resources/realtime";
import { formatEnergy, formatPower } from "../src/utils/format";
import { comfort, comfortProfile, energyProfile, energySummary } from "./helpers";

describe("confort", () => {
  it("applique une évaluation temps réel plus récente et ignore une plus ancienne", () => {
    const update = {
      zone_code: "meeting-room",
      assessed_at: "2026-10-27T12:05:00Z",
      temperature: 22,
      humidity: 45,
      temperature_status: "ok" as const,
      humidity_status: "ok" as const,
      level: "comfortable" as const,
      score: 100,
    };
    const updated = applyComfortUpdate(comfort, update);
    expect(updated[0].assessment).toMatchObject({ level: "comfortable", score: 100 });
    expect(updated[0].assessment).not.toHaveProperty("zone_code");
    expect(updated[1]).toBe(comfort[1]);

    const stale = applyComfortUpdate(updated, {
      ...update,
      assessed_at: "2026-10-27T11:00:00Z",
      level: "uncomfortable",
    });
    expect(stale[0].assessment?.level).toBe("comfortable");
  });

  it("valide les plages de confort, virgule décimale comprise", () => {
    const draft = { ...draftFromProfile(comfortProfile), temperature_min: "20,5" };
    expect(draft.temperature_max).toBe("24");
    const ok = validateProfileDraft(COMFORT_PROFILE_FIELDS, draft, comfortProfileErrors);
    expect(ok.values?.temperature_min).toBe(20.5);

    const inverted = validateProfileDraft(
      COMFORT_PROFILE_FIELDS,
      { ...draft, temperature_min: "25" },
      comfortProfileErrors,
    );
    expect(inverted.values).toBeUndefined();
    expect(inverted.errors.temperature_max).toMatch(/supérieure/);

    const invalid = validateProfileDraft(COMFORT_PROFILE_FIELDS, {
      ...draft,
      humidity_max: "120",
      humidity_min: "abc",
    });
    expect(invalid.errors).toEqual({ humidity_max: "Entre 0 et 100 %.", humidity_min: "Nombre attendu." });
  });
});

describe("énergie", () => {
  it("exige un nombre entier pour l'occupation par défaut", () => {
    const draft = { ...draftFromProfile(energyProfile().profile), default_occupancy: "2,5" };
    expect(validateProfileDraft(ENERGY_PROFILE_FIELDS, draft).errors.default_occupancy).toBe("Nombre entier attendu.");
    expect(
      validateProfileDraft(ENERGY_PROFILE_FIELDS, { ...draft, default_occupancy: "3" }).values?.default_occupancy,
    ).toBe(3);
  });

  it("additionne les espaces affichés", () => {
    const total = sumEnergy(energySummary.zones);
    expect(total.total_kwh).toBeCloseTo(14.4);
    expect(total.average_power_w).toBeCloseTo(600);
  });

  it("formate énergie et puissance", () => {
    expect(formatEnergy(0.85)).toBe("850 Wh");
    expect(formatEnergy(12.34)).toBe("12,3 kWh");
    expect(formatPower(450)).toBe("450 W");
    expect(formatPower(1234)).toBe("1,2 kW");
  });
});

describe("messages temps réel", () => {
  it("reconnaît les mises à jour de confort et d'énergie", () => {
    expect(parseRealtimeMessage(JSON.stringify({ event: "comfort.updated", data: { zone_code: "a" } }))).toEqual({
      event: "comfort.updated",
      data: { zone_code: "a" },
    });
    expect(parseRealtimeMessage(JSON.stringify({ event: "energy.updated", data: { zone_code: "a" } }))?.event).toBe(
      "energy.updated",
    );
    expect(parseRealtimeMessage(JSON.stringify({ event: "comfort.updated" }))).toBeNull();
  });
});
