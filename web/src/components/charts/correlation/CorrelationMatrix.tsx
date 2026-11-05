import { METRIC_VISUALS, type CorrelationMetric } from "../../../constants/metrics";
import { correlationColor, type PairResult } from "../../../utils/correlation";
import { signed } from "../../../utils/correlationInsights";

export function CorrelationMatrix({ metrics, pairs }: { metrics: CorrelationMetric[]; pairs: PairResult[] }) {
  const find = (a: CorrelationMetric, b: CorrelationMetric) =>
    pairs.find((p) => (p.a === a && p.b === b) || (p.a === b && p.b === a));
  return (
    <div
      className="corr-matrix"
      style={{ gridTemplateColumns: `minmax(92px,auto) repeat(${metrics.length}, minmax(0,1fr))` }}
    >
      <span />
      {metrics.map((m) => (
        <span key={m} className="corr-matrix-label">
          {METRIC_VISUALS[m].label}
        </span>
      ))}
      {metrics.map((row) => (
        <div className="corr-matrix-row" key={row} style={{ display: "contents" }}>
          <span className="corr-matrix-label row">{METRIC_VISUALS[row].label}</span>
          {metrics.map((col) => {
            const r = row === col ? 1 : (find(row, col)?.r ?? null);
            return (
              <div
                key={col}
                className={`corr-cell ${row === col ? "diag" : ""}`}
                style={{
                  background: row === col ? undefined : correlationColor(r),
                  color: r != null && Math.abs(r) > 0.45 && row !== col ? "#fff" : undefined,
                }}
              >
                {row === col ? "1" : r != null ? signed(r) : "—"}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
