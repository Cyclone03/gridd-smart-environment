import { describe, expect, it } from "vitest";
import { validateCustomRange } from "../src/resources/period";
import { periodFromSearchParams, periodToSearchParams, resolvePeriod } from "../src/utils/period";
import { DEFAULT_PERIOD } from "../src/constants/periods";

const now = new Date("2026-10-27T15:30:00");

describe("resolvePeriod", () => {
  it("calcule une période glissante à partir de l'heure courante", () => {
    const resolved = resolvePeriod({ kind: "preset", preset: "1h" }, now);
    expect(resolved.end).toEqual(now);
    expect(now.getTime() - resolved.start.getTime()).toBe(3_600_000);
    expect(resolved.live).toBe(true);
    expect(resolved.label).toBe("Dernière heure");
  });

  it("borne « aujourd'hui » et « hier » sur les journées locales", () => {
    const today = resolvePeriod({ kind: "preset", preset: "today" }, now);
    expect(today.start).toEqual(new Date("2026-10-27T00:00:00"));
    const yesterday = resolvePeriod({ kind: "preset", preset: "yesterday" }, now);
    expect(yesterday.start).toEqual(new Date("2026-10-26T00:00:00"));
    expect(yesterday.end).toEqual(new Date("2026-10-27T00:00:00"));
    expect(yesterday.live).toBe(false);
  });

  it("conserve les bornes d'une période personnalisée", () => {
    const resolved = resolvePeriod({ kind: "custom", start: "2026-10-20T12:00:00Z", end: "2026-10-21T12:00:00Z" }, now);
    expect(resolved.start.toISOString()).toBe("2026-10-20T12:00:00.000Z");
    expect(resolved.live).toBe(false);
    expect(resolved.label).toContain("→");
  });
});

describe("synchronisation avec l'URL", () => {
  it("fait l'aller-retour preset et plage personnalisée", () => {
    const preset = periodToSearchParams({ kind: "preset", preset: "7d" }, new URLSearchParams("zone=a"));
    expect(preset.toString()).toBe("zone=a&period=7d");
    expect(periodFromSearchParams(preset, DEFAULT_PERIOD)).toEqual({ kind: "preset", preset: "7d" });

    const custom = periodToSearchParams(
      { kind: "custom", start: "2026-10-20T12:00:00.000Z", end: "2026-10-21T12:00:00.000Z" },
      preset,
    );
    expect(custom.get("period")).toBeNull();
    expect(periodFromSearchParams(custom, DEFAULT_PERIOD).kind).toBe("custom");
  });

  it("ignore les valeurs invalides et accepte les anciens liens ?date=", () => {
    expect(periodFromSearchParams(new URLSearchParams("period=2ans"), DEFAULT_PERIOD)).toBe(DEFAULT_PERIOD);
    expect(periodFromSearchParams(new URLSearchParams("start=x&end=y"), DEFAULT_PERIOD)).toBe(DEFAULT_PERIOD);
    const legacy = periodFromSearchParams(new URLSearchParams("date=2026-10-20"), DEFAULT_PERIOD);
    expect(legacy.kind).toBe("custom");
    if (legacy.kind === "custom") {
      expect(new Date(legacy.end).getTime() - new Date(legacy.start).getTime()).toBe(86_400_000);
    }
  });
});

describe("validateCustomRange", () => {
  const options = { now, maxRangeDays: 31 };

  it("accepte une plage valide", () => {
    const result = validateCustomRange("2026-10-20T08:00", "2026-10-21T08:00", options);
    expect(result.errors).toEqual({});
    expect(result.start).toEqual(new Date("2026-10-20T08:00"));
  });

  it("signale chaque erreur sur le bon champ", () => {
    expect(validateCustomRange("", "2026-10-21T08:00", options).errors.start).toBeDefined();
    expect(validateCustomRange("2026-10-21T08:00", "2026-10-20T08:00", options).errors.end).toMatch(/postérieure/);
    expect(validateCustomRange("2026-10-28T08:00", "2026-10-29T08:00", options).errors.start).toMatch(/futur/);
    expect(validateCustomRange("2026-08-01T08:00", "2026-10-01T08:00", options).errors.end).toMatch(/31 jours/);
  });
});
