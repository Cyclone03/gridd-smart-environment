import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LOCALE } from "../../constants/app";
import { ENERGY_USE_ORDER, ENERGY_USES } from "../../constants/energy";
import type { EnergySeriesPoint } from "../../resources/energy";
import { formatEnergy } from "../../utils/format";

const DAY_MS = 86_400_000;

/** Énergie estimée d'un espace par créneau, empilée par usage. */
export function EnergySeriesChart({ points, spanMs }: { points: EnergySeriesPoint[]; spanMs: number }) {
  const tickFormat = new Intl.DateTimeFormat(
    LOCALE,
    spanMs > DAY_MS ? { day: "numeric", month: "short", hour: "2-digit" } : { hour: "2-digit", minute: "2-digit" },
  );
  const tooltipFormat = new Intl.DateTimeFormat(LOCALE, { weekday: "long", hour: "2-digit", minute: "2-digit" });

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={points} margin={{ top: 12, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#dfe7e4" strokeDasharray="3 5" vertical={false} />
        <XAxis
          dataKey="time"
          axisLine={false}
          tickLine={false}
          minTickGap={34}
          tick={{ fill: "#64716d", fontSize: 12 }}
          tickFormatter={(value) => tickFormat.format(new Date(String(value)))}
        />
        <YAxis
          axisLine={false}
          tickLine={false}
          tick={{ fill: "#64716d", fontSize: 12 }}
          tickFormatter={(value) => formatEnergy(Number(value))}
        />
        <Tooltip
          labelFormatter={(value) => tooltipFormat.format(new Date(String(value)))}
          formatter={(value, name) => [formatEnergy(Number(value)), name]}
          cursor={{ fill: "#f3f7f5" }}
        />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        {ENERGY_USE_ORDER.map((use) => (
          <Bar
            key={use}
            dataKey={`${use}_kwh`}
            name={ENERGY_USES[use].label}
            stackId="uses"
            fill={ENERGY_USES[use].color}
            isAnimationActive={false}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
