import { describe, expect, it } from "vitest";
import { parseRealtimeMessage } from "../src/resources/realtime";

describe("messages temps réel", () => {
  it("conserve les observations et alertes et ignore les anciens événements retirés", () => {
    expect(parseRealtimeMessage(JSON.stringify({ event: "alerts.changed" }))).toEqual({ event: "alerts.changed" });
    expect(parseRealtimeMessage(JSON.stringify({ event: "observation.created", data: { id: 1 } }))).toEqual({
      event: "observation.created",
      data: { id: 1 },
    });
    expect(parseRealtimeMessage(JSON.stringify({ event: "comfort.updated", data: {} }))).toBeNull();
    expect(parseRealtimeMessage(JSON.stringify({ event: "energy.updated", data: {} }))).toBeNull();
  });
});
