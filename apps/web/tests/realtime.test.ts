import { describe, expect, it } from "vitest";
import { parseRealtimeMessage } from "../src/resources/realtime";

const parse = (message: unknown) => parseRealtimeMessage(JSON.stringify(message));

describe("messages temps réel", () => {
  it("décode l'instantané et les changements avec leurs données", () => {
    const alerts = { active: [{ id: 1 }], history: [], history_days: 7 };
    expect(parse({ event: "dashboard.snapshot", data: { zones: [], latest: [], alerts } })).toEqual({
      event: "dashboard.snapshot",
      data: { zones: [], latest: [], alerts },
    });
    expect(parse({ event: "alerts.changed", data: alerts })).toEqual({ event: "alerts.changed", data: alerts });
    expect(parse({ event: "zones.changed", data: [{ code: "salle" }] })).toEqual({
      event: "zones.changed",
      data: [{ code: "salle" }],
    });
    expect(parse({ event: "observation.created", data: { id: 1 } })).toEqual({
      event: "observation.created",
      data: { id: 1 },
    });
    expect(parse({ event: "dashboard.error", detail: "Base indisponible" })).toEqual({
      event: "dashboard.error",
      detail: "Base indisponible",
    });
    expect(parse({ event: "pong" })).toEqual({ event: "pong" });
  });

  it("ignore les messages incomplets, invalides ou retirés", () => {
    // Ancien format sans données : le client ne refait plus de requête HTTP.
    expect(parse({ event: "alerts.changed" })).toBeNull();
    expect(parse({ event: "dashboard.snapshot", data: { zones: [] } })).toBeNull();
    expect(parse({ event: "zones.changed", data: {} })).toBeNull();
    expect(parse({ event: "comfort.updated", data: {} })).toBeNull();
    expect(parse({ event: "energy.updated", data: {} })).toBeNull();
    expect(parseRealtimeMessage("pas du JSON")).toBeNull();
    expect(parse(null)).toBeNull();
  });
});
