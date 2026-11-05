import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LOCALE } from "../../constants/app";
import { COMFORT_LEVELS } from "../../constants/comfort";
import type { ComfortHistoryPoint } from "../../resources/comfort";

const DAY_MS = 86_400_000;
const LEVELS = ["comfortable", "acceptable", "uncomfortable"] as const;

/**
 * Historique du confort : part de chaque niveau par créneau (barres empilées,
 * en %) et score moyen (courbe, sur 100).
 */
export function ComfortHistoryChart({ points, spanMs }: { points: ComfortHistoryPoint[]; spanMs: number }) {
  const tickFormat = new Intl.DateTimeFormat(
    LOCALE,
    spanMs > DAY_MS ? { day: "numeric", month: "short", hour: "2-digit" } : { hour: "2-digit", minute: "2-digit" },
  );
  const tooltipFormat = new Intl.DateTimeFormat(LOCALE, { weekday: "long", hour: "2-digit", minute: "2-digit" });
  const data = points.map((point) => {
    const total = point.comfortable + point.acceptable + point.uncomfortable;
    const share = (count: number) => (total ? Math.round((count / total) * 1000) / 10 : 0);
    return {
      time: point.time,
      score: point.score,
      comfortable: share(point.comfortable),
      acceptable: share(point.acceptable),
      uncomfortable: share(point.uncomfortable),
    };
  });

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={data} margin={{ top: 12, right: 16, left: -15, bottom: 0 }}>
        <CartesianGrid stroke="#dfe7e4" strokeDasharray="3 5" vertical={false} />
        <XAxis
          dataKey="time"
          axisLine={false}
          tickLine={false}
          minTickGap={34}
          tick={{ fill: "#64716d", fontSize: 12 }}
          tickFormatter={(value) => tickFormat.format(new Date(String(value)))}
        />
        <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: "#64716d", fontSize: 12 }} />
        <Tooltip
          labelFormatter={(value) => tooltipFormat.format(new Date(String(value)))}
          formatter={(value, name) =>
            name === "Score" ? [`${Math.round(Number(value))}/100`, name] : [`${Number(value)} %`, name]
          }
        />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        {LEVELS.map((level) => (
          <Bar
            key={level}
            dataKey={level}
            name={COMFORT_LEVELS[level].label}
            stackId="levels"
            fill={COMFORT_LEVELS[level].color}
            fillOpacity={0.28}
            isAnimationActive={false}
          />
        ))}
        <Line
          type="monotone"
          dataKey="score"
          name="Score"
          stroke="#18201e"
          strokeWidth={2.2}
          dot={false}
          connectNulls
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
