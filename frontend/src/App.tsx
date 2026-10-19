import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Building2,
  Droplets,
  Gauge,
  Leaf,
  Radio,
  RefreshCw,
  Search,
  Thermometer,
  Users,
  Volume2,
  Wind,
  X,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { loadDashboard } from "./api";
import type {
  Alert,
  MetricType,
  Observation,
  RealtimeStatus,
  Zone,
} from "./types";

const METRICS: Record<
  MetricType,
  { label: string; shortLabel: string; icon: typeof Thermometer; color: string }
> = {
  temperature: {
    label: "Température",
    shortLabel: "Temp.",
    icon: Thermometer,
    color: "#f4b860",
  },
  humidity: {
    label: "Humidité",
    shortLabel: "Humidité",
    icon: Droplets,
    color: "#58b9db",
  },
  co2: {
    label: "Qualité de l’air",
    shortLabel: "CO₂",
    icon: Wind,
    color: "#79d99d",
  },
  sound_level: {
    label: "Niveau sonore",
    shortLabel: "Son",
    icon: Volume2,
    color: "#b5a2ff",
  },
  occupancy: {
    label: "Occupation",
    shortLabel: "Présence",
    icon: Users,
    color: "#ef8e74",
  },
};

const METRIC_ORDER = Object.keys(METRICS) as MetricType[];

function observationTime(observation: Observation) {
  return observation.observed_at || observation.received_at;
}

function formatValue(value: number, type: MetricType) {
  return new Intl.NumberFormat("fr-CA", {
    maximumFractionDigits: type === "co2" || type === "occupancy" ? 0 : 1,
  }).format(value);
}

function formatTime(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("fr-CA", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function formatZoneType(value: string) {
  const labels: Record<string, string> = {
    server_room: "Salle serveur",
    meeting_room: "Salle de réunion",
    office: "Bureau",
    cubicle: "Cubicule",
    open_workspace: "Espace ouvert",
    classroom: "Salle de cours",
    lab: "Laboratoire",
    other: "Espace",
  };
  return labels[value] || value.replaceAll("_", " ");
}

function getMetricState(zone: Zone, observation?: Observation) {
  if (!observation) return "offline";
  if (observation.quality_status !== "normal") return "warning";

  const profile = zone.threshold_profile;
  if (!profile?.enabled) return "normal";

  if (
    observation.type === "temperature" &&
    (observation.value < profile.temperature_min ||
      observation.value > profile.temperature_max)
  ) {
    return "warning";
  }
  if (
    observation.type === "humidity" &&
    (observation.value < profile.humidity_min ||
      observation.value > profile.humidity_max)
  ) {
    return "warning";
  }
  if (
    observation.type === "co2" &&
    observation.value >= profile.co2_critical
  ) {
    return "critical";
  }
  if (
    observation.type === "co2" &&
    observation.value >= profile.co2_warning
  ) {
    return "warning";
  }
  return "normal";
}

function latestByZone(observations: Observation[], zones: Zone[]) {
  const zoneCodes = new Map(zones.map((zone) => [zone.id, zone.code]));
  const latest = new Map<string, Observation>();

  observations.forEach((observation) => {
    const code = observation.zone_code || zoneCodes.get(observation.zone);
    if (!code) return;
    const key = `${code}:${observation.type}`;
    const current = latest.get(key);
    if (
      !current ||
      new Date(observationTime(observation)).getTime() >
        new Date(observationTime(current)).getTime()
    ) {
      latest.set(key, { ...observation, zone_code: code });
    }
  });

  return latest;
}

function StatusPill({ status }: { status: RealtimeStatus }) {
  const copy = {
    connected: "Temps réel actif",
    connecting: "Connexion en cours",
    disconnected: "Temps réel interrompu",
  }[status];

  return (
    <div className={`status-pill status-${status}`}>
      <span className="status-pulse" />
      {copy}
    </div>
  );
}

function MetricTile({
  type,
  observation,
  state,
}: {
  type: MetricType;
  observation?: Observation;
  state: string;
}) {
  const metric = METRICS[type];
  const Icon = metric.icon;
  return (
    <div className={`metric-tile metric-${state}`}>
      <div className="metric-icon" style={{ color: metric.color }}>
        <Icon size={16} strokeWidth={1.8} />
      </div>
      <div>
        <span>{metric.shortLabel}</span>
        <strong>
          {observation ? formatValue(observation.value, type) : "—"}
          {observation && <small>{observation.unit}</small>}
        </strong>
      </div>
    </div>
  );
}

function ZoneCard({
  zone,
  latest,
  selected,
  alerts,
  onSelect,
}: {
  zone: Zone;
  latest: Map<string, Observation>;
  selected: boolean;
  alerts: number;
  onSelect: () => void;
}) {
  const observations = METRIC_ORDER.map((type) =>
    latest.get(`${zone.code}:${type}`),
  ).filter(Boolean) as Observation[];
  const updatedAt = observations
    .map((observation) => observationTime(observation))
    .sort()
    .at(-1);

  const states = METRIC_ORDER.map((type) =>
    getMetricState(zone, latest.get(`${zone.code}:${type}`)),
  );
  const health = alerts > 0 || states.includes("critical")
    ? "critical"
    : states.includes("warning")
      ? "warning"
      : observations.length
        ? "normal"
        : "offline";

  return (
    <button
      type="button"
      className={`zone-card ${selected ? "selected" : ""}`}
      onClick={onSelect}
    >
      <div className="zone-card-head">
        <div>
          <div className="zone-eyebrow">
            <span className={`health-dot health-${health}`} />
            {formatZoneType(zone.zone_type)}
          </div>
          <h3>{zone.name}</h3>
        </div>
        <ArrowUpRight size={18} />
      </div>

      <div className="zone-metrics">
        {METRIC_ORDER.map((type) => (
          <MetricTile
            key={type}
            type={type}
            observation={latest.get(`${zone.code}:${type}`)}
            state={getMetricState(zone, latest.get(`${zone.code}:${type}`))}
          />
        ))}
      </div>

      <div className="zone-card-foot">
        <span>Actualisé à {formatTime(updatedAt)}</span>
        {alerts > 0 && (
          <span className="alert-count">
            <AlertTriangle size={13} /> {alerts} alerte{alerts > 1 ? "s" : ""}
          </span>
        )}
      </div>
    </button>
  );
}

function SummaryCard({
  label,
  value,
  detail,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  icon: typeof Activity;
  tone: string;
}) {
  return (
    <div className="summary-card">
      <div className={`summary-icon tone-${tone}`}>
        <Icon size={19} />
      </div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
    </div>
  );
}

function ZoneDetail({
  zone,
  observations,
  latest,
  alerts,
  onClose,
}: {
  zone: Zone;
  observations: Observation[];
  latest: Map<string, Observation>;
  alerts: Alert[];
  onClose: () => void;
}) {
  const [metric, setMetric] = useState<MetricType>("temperature");

  useEffect(() => setMetric("temperature"), [zone.code]);

  const history = useMemo(
    () =>
      observations
        .filter(
          (observation) =>
            observation.zone_code === zone.code && observation.type === metric,
        )
        .slice(0, 60)
        .reverse()
        .map((observation) => ({
          value: observation.value,
          time: formatTime(observationTime(observation)),
        })),
    [metric, observations, zone.code],
  );

  const current = latest.get(`${zone.code}:${metric}`);
  const color = METRICS[metric].color;

  return (
    <aside className="detail-panel">
      <div className="detail-head">
        <div>
          <span>{formatZoneType(zone.zone_type)}</span>
          <h2>{zone.name}</h2>
        </div>
        <button className="icon-button" type="button" onClick={onClose} aria-label="Fermer">
          <X size={19} />
        </button>
      </div>

      <div className="metric-tabs">
        {METRIC_ORDER.map((type) => {
          const Icon = METRICS[type].icon;
          return (
            <button
              type="button"
              key={type}
              className={metric === type ? "active" : ""}
              onClick={() => setMetric(type)}
              title={METRICS[type].label}
            >
              <Icon size={16} />
              {METRICS[type].shortLabel}
            </button>
          );
        })}
      </div>

      <section className="chart-card">
        <div className="chart-heading">
          <div>
            <span>{METRICS[metric].label}</span>
            <strong>
              {current ? formatValue(current.value, metric) : "—"}
              {current && <small>{current.unit}</small>}
            </strong>
          </div>
          <div className="live-label"><Radio size={13} /> En direct</div>
        </div>

        <div className="chart-wrap">
          {history.length > 1 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                <defs>
                  <linearGradient id="metricGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={color} stopOpacity={0.34} />
                    <stop offset="100%" stopColor={color} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#17342b" strokeDasharray="3 5" vertical={false} />
                <XAxis dataKey="time" hide />
                <YAxis tick={{ fill: "#78968b", fontSize: 11 }} axisLine={false} tickLine={false} domain={["auto", "auto"]} />
                <Tooltip
                  contentStyle={{ background: "#0c211a", border: "1px solid #214a3d", borderRadius: 10 }}
                  labelStyle={{ color: "#9db5ac" }}
                  itemStyle={{ color }}
                />
                <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2.2} fill="url(#metricGradient)" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">En attente de davantage de mesures</div>
          )}
        </div>
      </section>

      <section className="detail-section">
        <div className="section-heading">
          <h3>Dernières mesures</h3>
          <span>{formatTime(current && observationTime(current))}</span>
        </div>
        <div className="detail-metrics">
          {METRIC_ORDER.map((type) => (
            <MetricTile
              key={type}
              type={type}
              observation={latest.get(`${zone.code}:${type}`)}
              state={getMetricState(zone, latest.get(`${zone.code}:${type}`))}
            />
          ))}
        </div>
      </section>

      <section className="detail-section alerts-section">
        <div className="section-heading">
          <h3>Alertes actives</h3>
          <span>{alerts.length}</span>
        </div>
        {alerts.length ? (
          <div className="detail-alerts">
            {alerts.slice(0, 4).map((alert) => (
              <div className={`detail-alert severity-${alert.severity}`} key={alert.id}>
                <AlertTriangle size={15} />
                <div>
                  <strong>{alert.message}</strong>
                  <span>{formatTime(alert.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="all-clear"><Leaf size={17} /> Aucun signal à surveiller</div>
        )}
      </section>
    </aside>
  );
}

export default function App() {
  const [zones, setZones] = useState<Zone[]>([]);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedZone, setSelectedZone] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<RealtimeStatus>("connecting");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const reconnectRef = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const data = await loadDashboard();
      setZones(data.zones);
      setObservations(data.observations);
      setAlerts(data.alerts);
      setLastUpdate(new Date());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Impossible de charger le dashboard.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => void refresh(), 60_000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let stopped = false;

    const connect = () => {
      if (stopped) return;
      setStatus("connecting");
      const scheme = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${scheme}://${window.location.host}/ws/dashboard/`);

      socket.onopen = () => setStatus("connected");
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data) as {
          event: string;
          data?: Observation;
        };
        if (message.event === "observation.created" && message.data) {
          setObservations((current) => [message.data!, ...current].slice(0, 1000));
          setLastUpdate(new Date());
        }
      };
      socket.onerror = () => setStatus("disconnected");
      socket.onclose = () => {
        setStatus("disconnected");
        if (!stopped) reconnectRef.current = window.setTimeout(connect, 3000);
      };
    };

    connect();
    return () => {
      stopped = true;
      if (reconnectRef.current) window.clearTimeout(reconnectRef.current);
      socket?.close();
    };
  }, []);

  const latest = useMemo(() => latestByZone(observations, zones), [observations, zones]);
  const normalizedQuery = query.trim().toLocaleLowerCase("fr-CA");
  const filteredZones = zones.filter((zone) =>
    `${zone.name} ${formatZoneType(zone.zone_type)}`
      .toLocaleLowerCase("fr-CA")
      .includes(normalizedQuery),
  );
  const selected = zones.find((zone) => zone.code === selectedZone);
  const zoneAlerts = (zone: Zone) => alerts.filter((alert) => alert.zone === zone.id);

  const average = (type: MetricType) => {
    const values = zones
      .map((zone) => latest.get(`${zone.code}:${type}`)?.value)
      .filter((value): value is number => value !== undefined);
    if (!values.length) return "—";
    return formatValue(values.reduce((sum, value) => sum + value, 0) / values.length, type);
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Accueil GRIDD">
          <span className="brand-mark"><Leaf size={19} /></span>
          <span><strong>GRIDD</strong><small>Smart Environment</small></span>
        </a>
        <div className="topbar-center">
          <span>École de technologie supérieure</span>
          <i />
          <span>Pavillon A · Laboratoire GRIDD</span>
        </div>
        <div className="topbar-actions">
          <StatusPill status={status} />
          <button className="icon-button" type="button" onClick={() => void refresh()} aria-label="Actualiser">
            <RefreshCw size={17} />
          </button>
        </div>
      </header>

      <main className="dashboard">
        <section className="hero-row">
          <div>
            <div className="overline"><Activity size={14} /> Vue d'ensemble</div>
            <h1>Le bâtiment, <em>en un regard.</em></h1>
            <p>Conditions ambiantes et occupation des espaces du GRIDD en temps réel.</p>
          </div>
          <div className="hero-meta">
            <span>Dernière donnée</span>
            <strong>{lastUpdate ? formatTime(lastUpdate.toISOString()) : "—"}</strong>
            <small>{new Intl.DateTimeFormat("fr-CA", { dateStyle: "long" }).format(new Date())}</small>
          </div>
        </section>

        {error && <div className="error-banner"><AlertTriangle size={17} />{error}</div>}

        <section className="summary-grid">
          <SummaryCard label="Espaces suivis" value={`${zones.length}`} detail="zones actives" icon={Building2} tone="green" />
          <SummaryCard label="Température moy." value={`${average("temperature")}°`} detail="tous les espaces" icon={Thermometer} tone="amber" />
          <SummaryCard label="CO₂ moyen" value={`${average("co2")} ppm`} detail="qualité de l’air" icon={Wind} tone="blue" />
          <SummaryCard label="Alertes actives" value={`${alerts.length}`} detail={alerts.length ? "attention requise" : "tout est stable"} icon={AlertTriangle} tone={alerts.length ? "red" : "green"} />
        </section>

        <section className="workspace">
          <div className="zones-column">
            <div className="section-bar">
              <div>
                <h2>Espaces surveillés</h2>
                <span>{filteredZones.length} zone{filteredZones.length > 1 ? "s" : ""}</span>
              </div>
              <label className="search-box">
                <Search size={16} />
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Rechercher un espace" />
              </label>
            </div>

            {loading ? (
              <div className="loading-grid">
                {[1, 2, 3, 4].map((item) => <div className="skeleton" key={item} />)}
              </div>
            ) : (
              <div className="zones-grid">
                {filteredZones.map((zone) => (
                  <ZoneCard
                    key={zone.id}
                    zone={zone}
                    latest={latest}
                    alerts={zoneAlerts(zone).length}
                    selected={zone.code === selectedZone}
                    onSelect={() => setSelectedZone(zone.code)}
                  />
                ))}
              </div>
            )}
          </div>

          <aside className="activity-rail">
            <div className="rail-heading">
              <div><Gauge size={17} /><h2>Activité récente</h2></div>
              <span>Live</span>
            </div>
            <div className="activity-list">
              {observations.slice(0, 9).map((observation) => {
                const metric = METRICS[observation.type];
                const Icon = metric.icon;
                return (
                  <button
                    type="button"
                    key={`${observation.id}-${observation.type}`}
                    className="activity-item"
                    onClick={() => setSelectedZone(observation.zone_code || zones.find((zone) => zone.id === observation.zone)?.code || null)}
                  >
                    <span className="activity-icon" style={{ color: metric.color }}><Icon size={15} /></span>
                    <span><strong>{observation.zone_name}</strong><small>{metric.shortLabel} · {formatTime(observationTime(observation))}</small></span>
                    <b>{formatValue(observation.value, observation.type)}<small>{observation.unit}</small></b>
                  </button>
                );
              })}
            </div>
          </aside>
        </section>
      </main>

      {selected && (
        <>
          <button className="panel-backdrop" type="button" onClick={() => setSelectedZone(null)} aria-label="Fermer le détail" />
          <ZoneDetail
            zone={selected}
            observations={observations.map((observation) => ({
              ...observation,
              zone_code: observation.zone_code || zones.find((zone) => zone.id === observation.zone)?.code,
            }))}
            latest={latest}
            alerts={zoneAlerts(selected)}
            onClose={() => setSelectedZone(null)}
          />
        </>
      )}
    </div>
  );
}
