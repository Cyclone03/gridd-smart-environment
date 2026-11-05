import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ENERGY_USE_ORDER, ENERGY_USES } from "../../constants/energy";
import type { ZoneEnergy } from "../../resources/energy";
import { formatEnergy, zoneDisplayName } from "../../utils/format";

/** Énergie estimée par espace, répartie par usage (barres horizontales empilées). */
export function EnergyBreakdownChart({ zones }: { zones: ZoneEnergy[] }) {
  const data = [...zones]
    .sort((a, b) => b.total_kwh - a.total_kwh)
    .map((zone) => ({ ...zone, name: zoneDisplayName({ code: zone.zone_code, name: zone.zone_name }) }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(180, data.length * 46 + 60)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 20, left: 10, bottom: 0 }}>
        <CartesianGrid stroke="#dfe7e4" strokeDasharray="3 5" horizontal={false} />
        <XAxis
          type="number"
          axisLine={false}
          tickLine={false}
          tick={{ fill: "#64716d", fontSize: 12 }}
          tickFormatter={(value) => formatEnergy(Number(value))}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={190}
          axisLine={false}
          tickLine={false}
          tick={{ fill: "#3c4845", fontSize: 12 }}
        />
        <Tooltip formatter={(value, name) => [formatEnergy(Number(value)), name]} cursor={{ fill: "#f3f7f5" }} />
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
