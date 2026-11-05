import { COMFORT_LEVELS } from "../../constants/comfort";
import type { ComfortLevel } from "../../resources/comfort";

/** Pastille du niveau de confort d'un espace. */
export function ComfortBadge({ level, score }: { level: ComfortLevel; score?: number | null }) {
  const visual = COMFORT_LEVELS[level];
  return (
    <span className={`comfort-badge ${visual.className}`}>
      <i aria-hidden="true" />
      {visual.label}
      {score != null && <b>{Math.round(score)}/100</b>}
    </span>
  );
}
