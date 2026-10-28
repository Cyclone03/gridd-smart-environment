import { useMemo } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LOCALE } from "../../../constants/app";
import { METRIC_VISUALS, type CorrelationMetric } from "../../../constants/metrics";
import type { Series } from "../../../utils/correlation";
import { signed } from "../../../utils/correlationInsights";

/** Superpose les séries centrées-réduites pour comparer leurs variations. */
export function NormalizedOverlay({ series, multiDay }: { series: Series[]; multiDay: boolean }) {
  const data = useMemo(() => {
    const stats = series.map((s) => {
      const vals = [...s.values.values()];
      const mean = vals.reduce((x, y) => x + y, 0) / vals.length;
      const sd = Math.sqrt(vals.reduce((x, y) => x + (y - mean) ** 2, 0) / vals.length) || 1;
      return { s, mean, sd };
    });
    const keys = Array.from(new Set(series.flatMap((s) => [...s.values.keys()]))).sort((x, y) => x - y);
    return keys.map((key) => {
      const row: Record<string, number | string | null> = {
        time: series.map((s) => s.times.get(key)).find(Boolean) || "",
      };
      for (const { s, mean, sd } of stats) {
        const v = s.values.get(key);
        row[s.type] = v == null ? null : Math.round(((v - mean) / sd) * 100) / 100;
      }
      return row;
    });
  }, [series]);
  const tickFormat = new Intl.DateTimeFormat(
    LOCALE,
    multiDay ? { weekday: "short", hour: "2-digit" } : { hour: "2-digit", minute: "2-digit" },
  );
  const tooltipFormat = new Intl.DateTimeFormat(LOCALE, { weekday: "long", hour: "2-digit", minute: "2-digit" });

  return (
    <div className="corr-overlay">
      <div className="corr-scatter-title">
        <strong>Évolution comparée (valeurs normalisées)</strong>
        <small>
          0 = moyenne de la période · ±1 = un écart-type. Des courbes qui bougent ensemble indiquent une corrélation.
        </small>
      </div>
      <div className="corr-legend">
        {series.map((s) => (
          <span key={s.type}>
            <i style={{ background: METRIC_VISUALS[s.type].color }} />
            {METRIC_VISUALS[s.type].label}
          </span>
        ))}
      </div>
      <div className="corr-overlay-chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 14, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="#dfe7e4" strokeDasharray="3 5" vertical={false} />
            <XAxis
              dataKey="time"
              axisLine={false}
              tickLine={false}
              minTickGap={40}
              tick={{ fill: "#64716d", fontSize: 11 }}
              tickFormatter={(v) => (v ? tickFormat.format(new Date(String(v))) : "")}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#64716d", fontSize: 11 }}
              domain={[-3, 3]}
              allowDataOverflow
              ticks={[-2, -1, 0, 1, 2]}
            />
            <ReferenceLine y={0} stroke="#9aa7a3" />
            <Tooltip
              labelFormatter={(v) => (v ? tooltipFormat.format(new Date(String(v))) : "")}
              formatter={(value, name) => [
                value == null ? "—" : `${signed(Number(value), 2)} σ`,
                METRIC_VISUALS[name as CorrelationMetric]?.label ?? String(name),
              ]}
            />
            {series.map((s) => (
              <Line
                key={s.type}
                type="monotone"
                dataKey={s.type}
                stroke={METRIC_VISUALS[s.type].color}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
