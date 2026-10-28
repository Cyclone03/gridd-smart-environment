import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { METRIC_UNITS, METRIC_VISUALS } from "../../../constants/metrics";
import type { PairResult } from "../../../utils/correlation";
import { pairLabel } from "../../../utils/correlationInsights";
import { formatNumber } from "../../../utils/format";

export function PairScatter({ pair }: { pair: PairResult }) {
  const a = { ...METRIC_VISUALS[pair.a], unit: METRIC_UNITS[pair.a] };
  const b = { ...METRIC_VISUALS[pair.b], unit: METRIC_UNITS[pair.b] };
  const xs = pair.points.map((p) => p.x);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const line: [{ x: number; y: number }, { x: number; y: number }] | null =
    pair.slope != null && pair.intercept != null && xMin < xMax
      ? [
          { x: xMin, y: pair.intercept + pair.slope * xMin },
          { x: xMax, y: pair.intercept + pair.slope * xMax },
        ]
      : null;
  return (
    <div className="corr-scatter">
      <div className="corr-scatter-title">
        <strong>{pairLabel(pair)}</strong>
        <small>Chaque point = un créneau · ligne = tendance linéaire</small>
      </div>
      <div className="corr-scatter-chart">
        {pair.points.length >= 3 ? (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 8, right: 14, bottom: 18, left: 4 }}>
              <CartesianGrid stroke="#dfe7e4" strokeDasharray="3 5" />
              <XAxis
                type="number"
                dataKey="x"
                name={a.label}
                domain={["auto", "auto"]}
                tick={{ fill: "#64716d", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => formatNumber(v, 1)}
                label={{
                  value: `${a.label} (${a.unit})`,
                  position: "insideBottom",
                  offset: -10,
                  fill: "#64716d",
                  fontSize: 11,
                }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name={b.label}
                domain={["auto", "auto"]}
                tick={{ fill: "#64716d", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => formatNumber(v, 0)}
                width={52}
                label={{
                  value: `${b.label} (${b.unit})`,
                  angle: -90,
                  position: "insideLeft",
                  offset: 14,
                  dy: 50,
                  fill: "#64716d",
                  fontSize: 11,
                }}
              />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                formatter={(value, name) => [
                  `${formatNumber(Number(value), 1)} ${name === a.label ? a.unit : b.unit}`,
                  String(name),
                ]}
              />
              <Scatter data={pair.points} fill={b.color} fillOpacity={0.55} />
              {line && (
                <ReferenceLine
                  segment={line}
                  stroke="#18201e"
                  strokeWidth={1.6}
                  strokeDasharray="5 4"
                  ifOverflow="extendDomain"
                />
              )}
            </ScatterChart>
          </ResponsiveContainer>
        ) : (
          <div className="chart-empty">Pas assez de points communs.</div>
        )}
      </div>
    </div>
  );
}
