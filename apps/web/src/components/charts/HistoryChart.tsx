import { memo, useMemo } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LOCALE } from "../../constants/app";
import { METRIC_VISUALS } from "../../constants/metrics";
import type { HistoryPoint } from "../../resources/history";
import type { MetricType } from "../../resources/observation";
import { formatValue } from "../../utils/format";

const DAY_MS = 86_400_000;
/** En dessous de ce nombre de créneaux, chaque point est marqué (sinon un point seul est invisible). */
const DOTS_BELOW = 12;

/**
 * Courbe des moyennes par créneau d'une mesure.
 *
 * L'animation Recharts est désactivée : le graphique est mis à jour en direct
 * (WebSocket) et chaque nouvelle donnée relançait l'animation d'apparition
 * depuis zéro, ce qui laissait la courbe vide tant que des mesures arrivaient.
 */
export const HistoryChart = memo(function HistoryChart({
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
  const tickFormat = useMemo(
    () =>
      new Intl.DateTimeFormat(
        LOCALE,
        multiDay ? { day: "numeric", month: "short", hour: "2-digit" } : { hour: "2-digit", minute: "2-digit" },
      ),
    [multiDay],
  );
  const tooltipFormat = useMemo(
    () =>
      new Intl.DateTimeFormat(LOCALE, {
        weekday: "long",
        day: "numeric",
        month: "long",
        hour: "2-digit",
        minute: "2-digit",
      }),
    [],
  );
  // Axe temporel réel (et non catégoriel) : un trou dans les mesures reste visible.
  const data = useMemo(
    () => points.map((point) => ({ ...point, ts: Date.parse(point.time), value: point.average })),
    [points],
  );
  const showDots = data.length < DOTS_BELOW;

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
          dataKey="ts"
          type="number"
          scale="time"
          domain={["dataMin", "dataMax"]}
          axisLine={false}
          tickLine={false}
          minTickGap={34}
          tick={{ fill: "#64716d", fontSize: 12 }}
          tickFormatter={(value) => tickFormat.format(new Date(Number(value)))}
        />
        <YAxis axisLine={false} tickLine={false} tick={{ fill: "#64716d", fontSize: 12 }} domain={["auto", "auto"]} />
        <Tooltip
          labelFormatter={(value) => tooltipFormat.format(new Date(Number(value)))}
          formatter={(value) => [`${formatValue(Number(value), metric)} ${unit}`, METRIC_VISUALS[metric].label]}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2.5}
          fill={`url(#${gradientId})`}
          isAnimationActive={false}
          dot={showDots ? { r: 3, fill: color, strokeWidth: 0 } : false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
});
