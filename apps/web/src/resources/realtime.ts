import type { ComfortUpdate } from "./comfort";
import type { Observation } from "./observation";

/** Messages reçus sur le WebSocket `/ws/dashboard/`. */
export type RealtimeMessage =
  | { event: "realtime.connected" }
  | { event: "observation.created"; data: Observation }
  | { event: "alerts.changed" }
  | { event: "comfort.updated"; data: ComfortUpdate }
  | { event: "energy.updated"; data: { zone_code: string } };

export function parseRealtimeMessage(raw: string): RealtimeMessage | null {
  try {
    const message = JSON.parse(raw) as { event?: unknown; data?: unknown };
    switch (message.event) {
      case "realtime.connected":
      case "alerts.changed":
        return { event: message.event };
      case "observation.created":
        return isObject(message.data) ? { event: "observation.created", data: message.data as Observation } : null;
      case "comfort.updated":
        return isObject(message.data) ? { event: "comfort.updated", data: message.data as ComfortUpdate } : null;
      case "energy.updated":
        return isObject(message.data) ? { event: "energy.updated", data: message.data as { zone_code: string } } : null;
      default:
        return null;
    }
  } catch {
    return null;
  }
}

function isObject(value: unknown): value is object {
  return Boolean(value) && typeof value === "object";
}
