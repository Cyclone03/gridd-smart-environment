import { describe, expect, it } from "vitest";
import {
  draftFromRule,
  emptyAlarmRuleDraft,
  parseDecimal,
  validateAlarmRuleDraft,
  type AlarmRuleDraft,
} from "../src/resources/alarmRule";
import { metadata, rule } from "./helpers";

const draft = (overrides: Partial<AlarmRuleDraft>): AlarmRuleDraft => ({
  ...emptyAlarmRuleDraft(),
  name: "Chaleur",
  metric: "temperature",
  operator: "gt",
  threshold: "28",
  ...overrides,
});

describe("validateAlarmRuleDraft", () => {
  it("produit la charge utile attendue par l'API", () => {
    const { payload, errors } = validateAlarmRuleDraft(
      draft({
        threshold: "27,5",
        min_duration: "5",
        min_duration_unit: "min",
        hysteresis: "0,5",
        zone: "meeting-room",
      }),
      metadata,
    );
    expect(errors).toEqual({});
    expect(payload).toEqual({
      name: "Chaleur",
      description: "",
      zone: "meeting-room",
      metric: "temperature",
      operator: "gt",
      threshold: 27.5,
      threshold_high: null,
      enabled: true,
      severity: "warning",
      min_duration_seconds: 300,
      hysteresis: 0.5,
    });
  });

  it("exige les champs obligatoires", () => {
    const { payload, errors } = validateAlarmRuleDraft(emptyAlarmRuleDraft(), metadata);
    expect(payload).toBeNull();
    expect(Object.keys(errors).sort()).toEqual(["metric", "name", "operator", "threshold"]);
  });

  it("valide les intervalles et l'hystérésis", () => {
    expect(validateAlarmRuleDraft(draft({ operator: "outside_range" }), metadata).errors.threshold_high).toMatch(
      /obligatoire/,
    );
    expect(
      validateAlarmRuleDraft(draft({ operator: "outside_range", threshold: "30", threshold_high: "20" }), metadata)
        .errors.threshold_high,
    ).toMatch(/supérieure/);
    expect(
      validateAlarmRuleDraft(
        draft({ operator: "outside_range", threshold: "20", threshold_high: "22", hysteresis: "1" }),
        metadata,
      ).errors.hysteresis,
    ).toMatch(/moitié/);
    expect(validateAlarmRuleDraft(draft({ hysteresis: "-1" }), metadata).errors.hysteresis).toBeDefined();
  });

  it("adapte la validation au type de mesure", () => {
    expect(validateAlarmRuleDraft(draft({ threshold: "500" }), metadata).errors.threshold).toMatch(/limites/);
    expect(
      validateAlarmRuleDraft(draft({ metric: "occupancy", threshold: "12,5" }), metadata).errors.threshold,
    ).toMatch(/entier/);
    expect(validateAlarmRuleDraft(draft({ metric: "occupancy", threshold: "30" }), metadata).payload?.threshold).toBe(
      30,
    );
    expect(validateAlarmRuleDraft(draft({ min_duration: "48", min_duration_unit: "min" }), metadata).errors).toEqual(
      {},
    );
    expect(
      validateAlarmRuleDraft(draft({ min_duration: "2000", min_duration_unit: "min" }), metadata).errors.min_duration,
    ).toBeDefined();
  });
});

describe("conversions", () => {
  it("lit les nombres au format français", () => {
    expect(parseDecimal("21,5")).toBe(21.5);
    expect(parseDecimal(" -3 ")).toBe(-3);
    expect(parseDecimal("abc")).toBeNull();
    expect(parseDecimal("")).toBeNull();
  });

  it("préremplit le formulaire depuis une règle", () => {
    expect(draftFromRule(rule({ min_duration_seconds: 300 }))).toMatchObject({
      min_duration: "5",
      min_duration_unit: "min",
      threshold: "28",
      zone: "meeting-room",
    });
    expect(draftFromRule(rule({ min_duration_seconds: 45, zone: null }))).toMatchObject({
      min_duration: "45",
      min_duration_unit: "s",
      zone: "",
    });
  });
});
