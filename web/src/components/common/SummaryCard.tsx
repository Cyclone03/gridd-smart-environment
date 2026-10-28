import type { LucideIcon } from "lucide-react";

export type Tone = "green" | "amber" | "blue" | "violet" | "red";

export function SummaryCard({
  label,
  value,
  detail,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone: Tone;
}) {
  return (
    <div className="summary-card">
      <div className={`summary-icon tone-${tone}`}>
        <Icon size={20} />
      </div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
    </div>
  );
}
