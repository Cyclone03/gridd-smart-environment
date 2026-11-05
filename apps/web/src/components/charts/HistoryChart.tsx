import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LOCALE } from "../../constants/app";
import { METRIC_VISUALS } from "../../constants/metrics";
import type { HistoryPoint } from "../../resources/history";
import type { MetricType } from "../../resources/observation";
import { formatValue } from "../../utils/format";

const DAY_MS = 86_400_000;

/** Courbe des moyennes par créneau d'une mesure. */
export function HistoryChart({
  points,
  metric,
  unit,
  spanMs,
}: {
  points: HistoryPoint[];
  metric: MetricType;
  unit: string;
  spanMs: number;
}) {
  const color = METRIC_VISUALS[metric].color;
  const gradientId = `history-gradient-${metric}`;
  const multiDay = spanMs > DAY_MS;
  const tickFormat = new Intl.DateTimeFormat(
    LOCALE,
    multiDay ? { day: "numeric", month: "short", hour: "2-digit" } : { hour: "2-digit", minute: "2-digit" },
  );
  const tooltipFormat = new Intl.DateTimeFormat(LOCALE, {
    weekday: "long",
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  });
  const data = points.map((point) => ({ ...point, value: point.average }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 12, right: 16, left: -15, bottom: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.32} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#dfe7e4" strokeDasharray="3 5" vertical={false} />
        <XAxis
          dataKey="time"
          axisLine={false}
          tickLine={false}
          minTickGap={34}
          tick={{ fill: "#64716d", fontSize: 12 }}
          tickFormatter={(value) => tickFormat.format(new Date(String(value)))}
        />
        <YAxis axisLine={false} tickLine={false} tick={{ fill: "#64716d", fontSize: 12 }} domain={["auto", "auto"]} />
        <Tooltip
          labelFormatter={(value) => tooltipFormat.format(new Date(String(value)))}
          formatter={(value) => [`${formatValue(Number(value), metric)} ${unit}`, METRIC_VISUALS[metric].label]}
        />
        <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2.5} fill={`url(#${gradientId})`} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
