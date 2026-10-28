import type { Observation } from "./observation";

/** Messages reçus sur le WebSocket `/ws/dashboard/`. */
export type RealtimeMessage =
  | { event: "realtime.connected" }
  | { event: "observation.created"; data: Observation }
  | { event: "alerts.changed" };

export function parseRealtimeMessage(raw: string): RealtimeMessage | null {
  try {
    const message = JSON.parse(raw) as { event?: unknown; data?: unknown };
    switch (message.event) {
      case "realtime.connected":
      case "alerts.changed":
        return { event: message.event };
      case "observation.created":
        return message.data && typeof message.data === "object"
          ? { event: "observation.created", data: message.data as Observation }
          : null;
      default:
        return null;
    }
  } catch {
    return null;
  }
}
