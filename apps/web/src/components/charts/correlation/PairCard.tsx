import { ArrowRightLeft } from "lucide-react";
import { METRIC_VISUALS } from "../../../constants/metrics";
import { correlationColor, isIndirect, strengthOf, type PairResult } from "../../../utils/correlation";
import { controlPhrase, formatP, pairLabel, signed } from "../../../utils/correlationInsights";

export function PairCard({ pair }: { pair: PairResult }) {
  const A = METRIC_VISUALS[pair.a].icon;
  const B = METRIC_VISUALS[pair.b].icon;
  const strength = pair.r != null ? strengthOf(pair.r) : null;
  const position = pair.r != null ? ((pair.r + 1) / 2) * 100 : 50;
  return (
    <div className="corr-pair">
      <div className="corr-pair-head">
        <span style={{ color: METRIC_VISUALS[pair.a].color }}>
          <A size={15} />
        </span>
        <ArrowRightLeft size={12} className="corr-arrow" />
        <span style={{ color: METRIC_VISUALS[pair.b].color }}>
          <B size={15} />
        </span>
        <strong>{pairLabel(pair)}</strong>
      </div>
      <div className="corr-r">
        <strong style={{ color: correlationColor(pair.r) }}>{pair.r != null ? signed(pair.r) : "—"}</strong>
        {strength && (
          <em className={`strength strength-${strength.level}`}>
            {strength.label}
            {pair.r != null && Math.abs(pair.r) >= 0.2 ? (pair.r > 0 ? " · positive" : " · négative") : ""}
          </em>
        )}
      </div>
      <div className="corr-scale" aria-hidden="true">
        <i style={{ left: `${position}%`, background: correlationColor(pair.r) }} />
      </div>
      <div className="corr-scale-labels">
        <span>−1</span>
        <span>0</span>
        <span>+1</span>
      </div>
      <dl>
        <div>
          <dt>Créneaux</dt>
          <dd>{pair.n}</dd>
        </div>
        <div>
          <dt>r²</dt>
          <dd>{pair.r != null ? `${Math.round(pair.r * pair.r * 100)} %` : "—"}</dd>
        </div>
        <div>
          <dt>Valeur p</dt>
          <dd>{formatP(pair.pValue)}</dd>
        </div>
      </dl>
      {isIndirect(pair) && (
        <span className="corr-indirect">Lien indirect · via {controlPhrase(pair.partial!.control)}</span>
      )}
    </div>
  );
}
