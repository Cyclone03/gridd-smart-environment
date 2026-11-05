import { Droplets, Thermometer } from "lucide-react";
import { HUMIDITY_STATUS_LABELS, TEMPERATURE_STATUS_LABELS } from "../../constants/comfort";
import type { ZoneComfort } from "../../resources/comfort";
import { formatNumber, formatTime, formatZoneType, zoneDisplayName } from "../../utils/format";
import { ComfortBadge } from "./ComfortBadge";

const one = (value: number) => formatNumber(value, 1).replace(/,0$/, "");

/** Confort actuel d'un espace : niveau, score, température et humidité face à leurs plages. */
export function ComfortZoneCard({
  zone,
  selected,
  onSelect,
}: {
  zone: ZoneComfort;
  selected: boolean;
  onSelect: () => void;
}) {
  const { assessment, profile } = zone;
  return (
    <button
      type="button"
      className={`comfort-card ${selected ? "selected" : ""}`}
      aria-pressed={selected}
      onClick={onSelect}
    >
      <div className="comfort-card-head">
        <div>
          <span className="zone-type">{formatZoneType(zone.zone_type)}</span>
          <h3>{zoneDisplayName({ code: zone.zone_code, name: zone.zone_name })}</h3>
        </div>
        <ComfortBadge level={assessment?.level ?? "unknown"} score={assessment?.score} />
      </div>
      <dl className="comfort-factors">
        <div>
          <dt>
            <Thermometer size={15} aria-hidden="true" /> Température
          </dt>
          <dd>{assessment?.temperature != null ? `${one(assessment.temperature)} °C` : "—"}</dd>
          <small>
            {TEMPERATURE_STATUS_LABELS[assessment?.temperature_status ?? "unknown"]} · plage{" "}
            {one(profile.temperature_min)}–{one(profile.temperature_max)} °C
          </small>
        </div>
        <div>
          <dt>
            <Droplets size={15} aria-hidden="true" /> Humidité
          </dt>
          <dd>{assessment?.humidity != null ? `${one(assessment.humidity)} %` : "—"}</dd>
          <small>
            {HUMIDITY_STATUS_LABELS[assessment?.humidity_status ?? "unknown"]} · plage {one(profile.humidity_min)}–
            {one(profile.humidity_max)} %
          </small>
        </div>
      </dl>
      <span className="comfort-card-foot">
        {assessment ? `Évalué à ${formatTime(assessment.assessed_at)}` : "Aucune évaluation pour le moment"}
        {zone.customized && " · plages personnalisées"}
      </span>
    </button>
  );
}
