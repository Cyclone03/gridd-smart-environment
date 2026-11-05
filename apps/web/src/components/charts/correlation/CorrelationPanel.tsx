import { GitCompareArrows, Info, Lightbulb } from "lucide-react";
import { useMemo, type ReactNode } from "react";
import { METRIC_VISUALS } from "../../../constants/metrics";
import type { ResolvedPeriod } from "../../../resources/period";
import { analyseAllPairs, MIN_POINTS, pairKey, type Series } from "../../../utils/correlation";
import { pairConclusion, pairLabel, synthesis } from "../../../utils/correlationInsights";
import { ErrorMessage, Loading } from "../../common/Feedback";
import { CorrelationMatrix } from "./CorrelationMatrix";
import { NormalizedOverlay } from "./NormalizedOverlay";
import { PairCard } from "./PairCard";
import { PairScatter } from "./PairScatter";

/**
 * Corrélations température / humidité / son d'un espace sur la période
 * appliquée. Les séries sont chargées par la vue (useCorrelationSeries).
 */
export function CorrelationPanel({
  zoneName,
  supported,
  period,
  series,
  loading,
  error,
  onRetry,
}: {
  zoneName: string;
  /** Faux si l'espace mesure moins de deux grandeurs comparables. */
  supported: boolean;
  period: ResolvedPeriod;
  series: Series[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  const pairs = useMemo(() => analyseAllPairs(series ?? []), [series]);
  const available = useMemo(() => (series ?? []).map((s) => s.type), [series]);
  const conclusions = useMemo(() => synthesis(pairs, available), [pairs, available]);
  const bucketMinutes = series?.[0]?.bucketMinutes ?? 15;
  const multiDay = period.end.getTime() - period.start.getTime() > 86_400_000;

  let body: ReactNode;
  if (!supported)
    body = (
      <div className="corr-empty">
        Cet espace ne mesure pas au moins deux grandeurs parmi la température, l’humidité et le niveau sonore.
      </div>
    );
  else if (error)
    body = (
      <div className="corr-empty">
        <ErrorMessage onRetry={onRetry}>{error}</ErrorMessage>
      </div>
    );
  else if (loading && !series)
    body = (
      <div className="corr-empty">
        <Loading label="Calcul des corrélations…" />
      </div>
    );
  else if (!series || series.length < 2)
    body = (
      <div className="corr-empty">
        Il faut au moins deux mesures avec {MIN_POINTS} créneaux ou plus pour calculer une corrélation.
        {series?.length === 1
          ? ` Seule la mesure « ${METRIC_VISUALS[series[0].type].label} » est assez fournie.`
          : ""}{" "}
        Essayez une période plus longue.
      </div>
    );
  else
    body = (
      <>
        <div className="corr-top">
          <div className="corr-pairs">
            {pairs.map((p) => (
              <PairCard key={pairKey(p.a, p.b)} pair={p} />
            ))}
          </div>
          {available.length > 2 && (
            <div className="corr-matrix-card">
              <span className="corr-sub">Matrice de corrélation</span>
              <CorrelationMatrix metrics={available} pairs={pairs} />
              <div className="corr-matrix-legend">
                <span>Négative</span>
                <i />
                <span>Positive</span>
              </div>
            </div>
          )}
        </div>
        <NormalizedOverlay series={series} multiDay={multiDay} />
        <div className="corr-scatters">
          {pairs.map((p) => (
            <PairScatter key={pairKey(p.a, p.b)} pair={p} />
          ))}
        </div>
        <div className="corr-conclusions">
          <h4>
            <Lightbulb size={17} /> Conclusions
          </h4>
          <div className="corr-conclusion-list">
            {pairs.map((p) => (
              <div className="corr-conclusion" key={pairKey(p.a, p.b)}>
                <strong>{pairLabel(p)}</strong>
                <p>{pairConclusion(p, bucketMinutes)}</p>
              </div>
            ))}
          </div>
          <div className="corr-synthesis">
            <strong>
              Synthèse pour {zoneName} · {period.label}
            </strong>
            <ul>
              {conclusions.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </div>
          <p className="corr-note">
            <Info size={13} /> Coefficient de Pearson calculé sur les moyennes par créneau de {bucketMinutes} min. Une
            corrélation indique que deux mesures varient ensemble, pas que l’une cause l’autre. La valeur p est
            indicative : des mesures consécutives ne sont pas totalement indépendantes.
          </p>
        </div>
      </>
    );

  return (
    <section className="corr-card" aria-busy={loading}>
      <div className="corr-head">
        <div>
          <span className="section-kicker">
            <GitCompareArrows size={13} /> Corrélations entre systèmes
          </span>
          <h3>Température, humidité et niveau sonore</h3>
          <p>
            Comment les mesures de cet espace évoluent les unes par rapport aux autres ·{" "}
            <span className="corr-period">{period.label}</span>
          </p>
        </div>
      </div>
      {body}
    </section>
  );
}
