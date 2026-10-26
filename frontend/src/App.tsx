import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, Building2, CalendarDays, Check, CheckCircle2, ChevronDown, ChevronLeft, ChevronRight, Droplets, Eye, Leaf, RefreshCw, Search, Thermometer, Users, Volume2, Wind } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { loadActiveAlerts, loadDashboard, loadLatestObservations, loadZoneDayHistory } from "./api";
import { CorrelationPanel } from "./correlations";
import type { Alert, MetricType, Observation, RealtimeStatus, Zone, ZoneHistory } from "./types";

type Page = "overview" | "spaces" | "history" | "alerts";
const PAGE_PATHS: Record<Page, string> = { overview: "/", spaces: "/spaces/", history: "/history/", alerts: "/alerts/" };
function pageFromPath(pathname: string): Page {
  if (pathname.startsWith("/spaces")) return "spaces";
  if (pathname.startsWith("/history")) return "history";
  if (pathname.startsWith("/alerts")) return "alerts";
  return "overview";
}
const METRICS: Record<MetricType, { label: string; shortLabel: string; icon: typeof Thermometer; color: string }> = {
  temperature: { label: "Température", shortLabel: "Température", icon: Thermometer, color: "#d98519" },
  humidity: { label: "Humidité", shortLabel: "Humidité", icon: Droplets, color: "#2184a7" },
  sound_level: { label: "Niveau sonore", shortLabel: "Son", icon: Volume2, color: "#7259bd" },
  occupancy: { label: "Occupation", shortLabel: "Présence", icon: Users, color: "#c55d45" },
};
const METRIC_ORDER = Object.keys(METRICS) as MetricType[];
const READ_ALERTS_KEY = "gridd-alerts-read-ids";

function observationTime(observation: Observation) { return observation.observed_at || observation.received_at; }
function formatValue(value: number, type: MetricType) {
  return new Intl.NumberFormat("fr-CA", { maximumFractionDigits: type === "occupancy" ? 0 : 1 }).format(value);
}
function formatTime(value?: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("fr-CA", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(value));
}
function formatDate(value: Date) {
  return new Intl.DateTimeFormat("fr-CA", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(value);
}
function dateKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
function formatZoneType(value: string) {
  const labels: Record<string, string> = { server_room: "Salle serveur", meeting_room: "Salle de réunion", office: "Bureau", cubicle: "Cubicule", open_workspace: "Espace ouvert", classroom: "Salle de cours", lab: "Laboratoire", other: "Espace" };
  return labels[value] || value.replaceAll("_", " ");
}
function latestByZone(observations: Observation[], zones: Zone[]) {
  const zoneCodes = new Map(zones.map((zone) => [zone.id, zone.code]));
  const latest = new Map<string, Observation>();
  observations.forEach((observation) => {
    const code = observation.zone_code || zoneCodes.get(observation.zone);
    if (!code) return;
    const key = `${code}:${observation.type}`;
    const current = latest.get(key);
    if (!current || new Date(observationTime(observation)).getTime() > new Date(observationTime(current)).getTime()) latest.set(key, { ...observation, zone_code: code });
  });
  return latest;
}

function StatusPill({ status }: { status: RealtimeStatus }) {
  const label = { connected: "WebSocket connecté", connecting: "Connexion WebSocket", disconnected: "WebSocket interrompu" }[status];
  return <div className={`status-pill status-${status}`}><span className="status-pulse" />{label}</div>;
}
function MetricTile({ type, observation }: { type: MetricType; observation?: Observation }) {
  const metric = METRICS[type]; const Icon = metric.icon;
  if (metric.label === "Température" || metric.label === "Humidité" || metric.label === "Niveau sonore") {return <div className={`metric-tile ${observation ? "" : "metric-missing"}`}><div className="metric-icon" style={{ color: metric.color }}><Icon size={17} /></div><div><span>{metric.shortLabel}</span><strong>{observation ? formatValue(observation.value, type) : "—"}{observation && <small>{observation.unit}</small>}</strong>{observation && <time dateTime={observationTime(observation)}>Mesuré à {formatTime(observationTime(observation))}</time>}</div></div>;}
}
function MetricTile2({ type, observation }: { type: MetricType; observation?: Observation }) {
  const metric = METRICS[type]; const Icon = metric.icon;
  if (metric.label === "Température" || metric.label === "Humidité") {return <div className={`metric-tile ${observation ? "" : "metric-missing"}`}><div className="metric-icon" style={{ color: metric.color }}><Icon size={17} /></div><div><span>{metric.shortLabel}</span><strong>{observation ? formatValue(observation.value, type) : "—"}{observation && <small>{observation.unit}</small>}</strong>{observation && <time dateTime={observationTime(observation)}>Mesuré à {formatTime(observationTime(observation))}</time>}</div></div>;}
}
function MetricTile3({ type, observation }: { type: MetricType; observation?: Observation }) {
  const metric = METRICS[type]; const Icon = metric.icon;
  if (metric.label === "Occupation") {return <div className={`metric-tile ${observation ? "" : "metric-missing"}`}><div className="metric-icon" style={{ color: metric.color }}><Icon size={17} /></div><div><span>{metric.shortLabel}</span><strong>{observation ? formatValue(observation.value, type) : "—"}{observation && <small>{observation.unit}</small>}</strong>{observation && <time dateTime={observationTime(observation)}>Mesuré à {formatTime(observationTime(observation))}</time>}</div></div>;}
}
function ZoneCard({ zone, latest, alertCount, onHistory }: { zone: Zone; latest: Map<string, Observation>; alertCount: number; onHistory: () => void }) {
  const values = METRIC_ORDER.map((type) => latest.get(`${zone.code}:${type}`)).filter(Boolean) as Observation[];
  const newest = values.map(observationTime).sort().at(-1);
  if (zone.name != "Salle du GRIDD") {return <article className="zone-card"><div className="zone-card-head"><div><span className="zone-type">{formatZoneType(zone.zone_type)}</span><h3>{zone.name==="occupancy-camera" ? "GRIDD" : zone.name}</h3></div>{alertCount > 0 && <span className="zone-alert-count">{alertCount} alerte{alertCount > 1 ? "s" : ""}</span>}</div><div className="zone-metrics">{zone.name === "Salle de réunion" || zone.name === "Bureau des professeurs" || zone.name === "Cubicule de travail individuel 01" || zone.name === "Cubicule de travail individuel 02" ? METRIC_ORDER.map((type) => <MetricTile key={type} type={type} observation={latest.get(`${zone.code}:${type}`)} />) : zone.name === "Espace de travail ouvert" || zone.name === "Salle des serveurs et équipements" ? METRIC_ORDER.map((type) => <MetricTile2 key={type} type={type} observation={latest.get(`${zone.code}:${type}`)} />) : METRIC_ORDER.map((type) => <MetricTile3 key={type} type={type} observation={latest.get(`${zone.code}:${type}`)} />)}</div><div className="zone-card-foot"><span>Dernière mesure : {formatTime(newest)}</span><button type="button" onClick={onHistory}>Voir l’historique</button></div></article>;}
}
function SummaryCard({ label, value, detail, icon: Icon, tone }: { label: string; value: string; detail: string; icon: typeof Activity; tone: string }) {
  return <div className="summary-card"><div className={`summary-icon tone-${tone}`}><Icon size={20} /></div><div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div></div>;
}

function SpacesView({ zones, latest, alerts, loading, onHistory }: { zones: Zone[]; latest: Map<string, Observation>; alerts: Alert[]; loading: boolean; onHistory: (code: string) => void }) {
  const [query, setQuery] = useState("");
  const filteredZones = zones.filter((zone) => `${zone.name} ${formatZoneType(zone.zone_type)}`.toLocaleLowerCase("fr-CA").includes(query.trim().toLocaleLowerCase("fr-CA")));
  return <main className="dashboard page-view"><header className="page-head"><div><span className="overline"><Building2 size={15} /> Espaces</span><h1>Tous les espaces surveillés</h1></div></header><section className="spaces-section"><div className="section-bar"><div><span className="section-kicker">Toutes les zones</span><h2>Espaces surveillés</h2></div><label className="search-box"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Rechercher un espace" /></label></div><div className="zones-grid">{loading ? Array.from({ length: 6 }, (_, index) => <div className="zone-card skeleton" key={index} />) : filteredZones.map((zone) => <ZoneCard key={zone.code} zone={zone} latest={latest} alertCount={alerts.filter((alert) => alert.zone === zone.id).length} onHistory={() => onHistory(zone.code)} />)}</div></section></main>;
}

function startOfWeek(value: Date) {
  const date = new Date(value);
  date.setHours(12, 0, 0, 0);
  const mondayOffset = (date.getDay() + 6) % 7;
  date.setDate(date.getDate() - mondayOffset);
  return date;
}

function HistoryView({ zones, latest, initialZone }: { zones: Zone[]; latest: Map<string, Observation>; initialZone: string | null }) {
  const today = useMemo(() => { const value = new Date(); value.setHours(12, 0, 0, 0); return value; }, []);
  const currentWeek = useMemo(() => startOfWeek(today), [today]);
  const initialParams = useMemo(() => new URLSearchParams(window.location.search), []);
  const requestedMetric = initialParams.get("metric") as MetricType | null;
  const requestedDate = initialParams.get("date");
  const safeInitialDate = requestedDate && /^\d{4}-\d{2}-\d{2}$/.test(requestedDate) && new Date(`${requestedDate}T12:00:00`) <= today ? requestedDate : dateKey(today);
  const [zoneCode, setZoneCode] = useState(initialZone || initialParams.get("zone") || zones[0]?.code || "");
  const [metric, setMetric] = useState<MetricType>(requestedMetric && METRIC_ORDER.includes(requestedMetric) ? requestedMetric : "temperature");
  const [selectedDate, setSelectedDate] = useState(safeInitialDate);
  const [weekStart, setWeekStart] = useState(startOfWeek(new Date(`${safeInitialDate}T12:00:00`)));
  const [history, setHistory] = useState<ZoneHistory | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startTime, setStartTime] = useState("00:00");
  const [endTime, setEndTime] = useState("23:45");

  useEffect(() => {
    if (initialZone) setZoneCode(initialZone);
    else if (zones.length && (!zoneCode || !zones.some((item) => item.code === zoneCode))) setZoneCode(zones[0].code);
  }, [initialZone, zoneCode, zones]);
  useEffect(() => {
    if (!zoneCode) return;
    const params = new URLSearchParams({ zone: zoneCode, metric, date: selectedDate });
    window.history.replaceState({}, "", `/history/?${params.toString()}`);
  }, [metric, selectedDate, zoneCode]);
  const days = useMemo(() => Array.from({ length: 7 }, (_, index) => { const date = new Date(weekStart); date.setDate(date.getDate() + index); return date; }), [weekStart]);
  const changeWeek = (offset: number) => {
    const next = new Date(weekStart); next.setDate(next.getDate() + offset * 7);
    if (next > currentWeek) return;
    const selected = new Date(`${selectedDate}T12:00:00`); selected.setDate(selected.getDate() + offset * 7);
    if (selected > today) selected.setTime(today.getTime());
    setWeekStart(next); setSelectedDate(dateKey(selected));
  };
  const chooseDate = (key: string) => { const value = new Date(`${key}T12:00:00`); setSelectedDate(key); setWeekStart(startOfWeek(value)); };

  useEffect(() => {
    if (!zoneCode) return;
    let cancelled = false; setLoading(true); setError(null); setHistory(null);
    void loadZoneDayHistory(zoneCode, metric, selectedDate).then((data) => { if (!cancelled) setHistory(data); }).catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : "Historique indisponible."); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [metric, selectedDate, zoneCode]);

  const zone = zones.find((item) => item.code === zoneCode);
  const current = latest.get(`${zoneCode}:${metric}`);
  const chartData = (history?.points || []).map((point) => ({ ...point, value: point.average }));
  const trend = history && history.statistics.count > 0 ? { rising: "En hausse", falling: "En baisse", stable: "Stable" }[history.statistics.trend] : "—";
  const color = METRICS[metric].color;
  const weekEnd = days[6];
  const displayedData = useMemo(() => {
  return chartData.filter((point) => {
    const time = new Date(point.time);
    const minutes = time.getHours() * 60 + time.getMinutes();

    const [startHour, startMinute] = startTime.split(":").map(Number);
    const [endHour, endMinute] = endTime.split(":").map(Number);

    const start = startHour * 60 + startMinute;
    const end = endHour * 60 + endMinute;

    return start <= end && minutes >= start && minutes <= end;
  });
}, [chartData, startTime, endTime]);

  return <main className="dashboard page-view">
    <header className="page-head"><div><span className="overline"><CalendarDays size={15} /> Analyse historique</span><h1>Historique par espace</h1><p>Choisissez un espace, une mesure et une date enregistrée.</p></div></header>
    <section className="history-workspace">
      <aside className="space-selector" aria-label="Sélectionner un espace"><span className="section-kicker">Espaces suivis</span>{zones.map((item) => {
        const available = METRIC_ORDER.filter((type) => latest.has(`${item.code}:${type}`)).length;
        if (item.name != "Salle du GRIDD") {return <button key={item.code} type="button" className={zoneCode === item.code ? "active" : ""} onClick={() => setZoneCode(item.code)}><span>{item.name === "occupancy-camera" ? "GRIDD":item.name}</span><small>{formatZoneType(item.zone_type)} · {available}/{available} mesures disponibles</small><ChevronRight size={16} /></button>;}
      })}</aside>
      <div className="history-main">
        <div className="history-title"><div><span>{zone ? formatZoneType(zone.zone_type) : "Espace"}</span><h2>{zone?.name === "occupancy-camera" ? "GRIDD" : zone?.name}</h2></div><div className="current-reading"><span>Dernière mesure reçue</span><strong>{current ? `${formatValue(current.value, metric)} ${current.unit}` : "—"}</strong><small>{current ? formatTime(observationTime(current)) : "Aucune mesure"}</small></div></div>
        <div className="metric-tabs">{METRIC_ORDER.map((type) => { const Icon = METRICS[type].icon; const hasValue = latest.has(`${zoneCode}:${type}`); if (((zone?.name === "Salle de réunion" || zone?.name === "Bureau des professeurs" || zone?.name === "Cubicule de travail individuel 01" || zone?.name === "Cubicule de travail individuel 02") && (METRICS[type].label === "Température" || METRICS[type].label === "Humidité" || METRICS[type].label === "Niveau sonore")) || ((zone?.name === "Espace de travail ouvert" || zone?.name === "Salle des serveurs et équipements") && (METRICS[type].label === "Température" || METRICS[type].label === "Humidité")) || ((zone?.name === "occupancy-camera") && (METRICS[type].label === "Occupation"))) {return <button type="button" key={type} className={metric === type ? "active" : ""} onClick={() => setMetric(type)}><Icon size={16} />{METRICS[type].label}<i className={hasValue ? "available" : "missing"} /></button>; }})}</div>
        <div className="week-toolbar"><button type="button" onClick={() => changeWeek(-1)}><ChevronLeft size={17} /> Semaine précédente</button><div><strong>{new Intl.DateTimeFormat("fr-CA", { day: "numeric", month: "long" }).format(weekStart)} – {new Intl.DateTimeFormat("fr-CA", { day: "numeric", month: "long", year: "numeric" }).format(weekEnd)}</strong><label>Aller à une date<input type="date" max={dateKey(today)} value={selectedDate} onChange={(event) => chooseDate(event.target.value)} /></label></div><button type="button" disabled={weekStart >= currentWeek} onClick={() => changeWeek(1)}>Semaine suivante <ChevronRight size={17} /></button></div>
        <div className="weekday-scroller" aria-label="Choisir un jour">{days.map((day) => { const key = dateKey(day); const future = day > today; return <button type="button" key={key} disabled={future} className={selectedDate === key ? "active" : ""} onClick={() => chooseDate(key)}><span>{new Intl.DateTimeFormat("fr-CA", { weekday: "long" }).format(day)}</span><small>{new Intl.DateTimeFormat("fr-CA", { day: "numeric", month: "long" }).format(day)}</small></button>; })}</div>
        <section className="history-chart-card"><div className="chart-heading"><div><span>{METRICS[metric].label}</span><strong>{formatDate(new Date(`${selectedDate}T12:00:00`))}</strong></div><small>Regroupement par {history?.bucket_minutes || 15} min</small></div><div>
  <label>
    De :
    <input
      type="time"
      value={startTime}
      onChange={(event) => setStartTime(event.target.value)}
    />
  </label>

  <label>
    À :
    <input
      type="time"
      value={endTime}
      onChange={(event) => setEndTime(event.target.value)}
    />
  </label>
</div><div className="chart-wrap">{chartData.length > 0 ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={displayedData} margin={{ top: 12, right: 16, left: -15, bottom: 0 }}><defs><linearGradient id="historyGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity={0.32} /><stop offset="100%" stopColor={color} stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#dfe7e4" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="time" axisLine={false} tickLine={false} minTickGap={34} tick={{ fill: "#64716d", fontSize: 12 }} tickFormatter={(value) => new Intl.DateTimeFormat("fr-CA", { hour: "2-digit", minute: "2-digit" }).format(new Date(String(value)))} /><YAxis axisLine={false} tickLine={false} tick={{ fill: "#64716d", fontSize: 12 }} domain={["auto", "auto"]} /><Tooltip labelFormatter={(value) => new Intl.DateTimeFormat("fr-CA", { weekday: "long", hour: "2-digit", minute: "2-digit" }).format(new Date(String(value)))} formatter={(value) => [String(value), METRICS[metric].label]} /><Area type="monotone" dataKey="value" stroke={color} strokeWidth={2.5} fill="url(#historyGradient)" /></AreaChart></ResponsiveContainer> : <div className="chart-empty">{loading ? "Chargement…" : error || "Aucune mesure enregistrée pour cette sélection."}</div>}</div><div className="history-stats"><div><span>Moyenne</span><strong>{history?.statistics.average != null ? `${formatValue(history.statistics.average, metric)} ${history.unit}` : "—"}</strong></div><div><span>Minimum</span><strong>{history?.statistics.minimum != null ? `${formatValue(history.statistics.minimum, metric)} ${history.unit}` : "—"}</strong></div><div><span>Maximum</span><strong>{history?.statistics.maximum != null ? `${formatValue(history.statistics.maximum, metric)} ${history.unit}` : "—"}</strong></div><div><span>Mesures</span><strong>{history?.statistics.count ?? 0}</strong></div><div><span>Tendance</span><strong>{trend}</strong></div><div><span>Prédiction</span><strong>{chartData.at(-1)?.value != null && METRICS[metric].label === "Température" && trend === "En hausse" ? Math.round((chartData.at(-1)!.value + 0.1)*10)/10 : chartData.at(-1)?.value != null && METRICS[metric].label === "Température" && trend === "En baisse" ? Math.round((chartData.at(-1)!.value - 0.1)*10)/10 : chartData.at(-1)?.value != null && METRICS[metric].label === "Humidité" && trend === "En hausse" ? Math.round((chartData.at(-1)!.value + 1)*10)/10 : chartData.at(-1)?.value != null && METRICS[metric].label === "Humidité" && trend === "En baisse" ? Math.round((chartData.at(-1)!.value - 1)*10)/10 : chartData.at(-1)?.value != null && METRICS[metric].label === "Niveau sonore" && trend === "En hausse" ? Math.round((chartData.at(-1)!.value + 5)*10)/10 : chartData.at(-1)?.value != null && METRICS[metric].label === "Niveau sonore" && trend === "En baisse" ? Math.round((chartData.at(-1)!.value - 5)*10)/10 : chartData.at(-1)?.value != null && METRICS[metric].label === "Occupation" && trend === "En hausse" ? Math.round((chartData.at(-1)!.value + 1)*10)/10 : chartData.at(-1)?.value != null && METRICS[metric].label === "Occupation" && trend === "En baisse" ? Math.round((chartData.at(-1)!.value - 1)*10)/10 : chartData.at(-1)?.value != null && trend === "Stable" ? Math.round((chartData.at(-1)!.value)*10)/10 : "—"}</strong></div></div></section>
        {zoneCode && <CorrelationPanel zoneCode={zoneCode} zoneName={zone?.name} selectedDate={selectedDate} />}
      </div>
    </section>
  </main>;
}

function AlertsView({ alerts, zones, readIds, onRead, onReadAll }: { alerts: Alert[]; zones: Zone[]; readIds: number[]; onRead: (id: number) => void; onReadAll: () => void }) {
  const [ruleZone, setRuleZone] = useState(zones[0]?.code || "");
  const [openAlert, setOpenAlert] = useState<number | null>(null);
  useEffect(() => { if (!ruleZone && zones[0]) setRuleZone(zones[0].code); }, [ruleZone, zones]);
  const zone = zones.find((item) => item.code === ruleZone); const profile = zone?.threshold_profile;
  const unread = alerts.filter((alert) => !readIds.includes(alert.id)).length;
  const severityLabel = { info: "Information", warning: "Avertissement", critical: "Critique" };
  const [severityFilter, setSeverityFilter] = useState<"all" | "info" | "warning" | "critical">("all");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const filteredAlerts = alerts.filter((alert) => severityFilter === "all" || alert.severity === severityFilter).sort((a, b) => {const dateA = new Date(a.created_at).getTime(); const dateB = new Date(b.created_at).getTime(); return sortOrder === "asc" ? dateA - dateB : dateB - dateA;});
  return <main className="dashboard page-view"><header className="page-head"><div><span className="overline"><AlertTriangle size={15} /> Alertes</span><h1>Alertes actives et règles appliquées</h1><p>Cliquez sur une alerte pour la consulter. Elle reste visible tant qu’elle est active.</p></div><div className="alert-page-count"><span>{unread} non consultée{unread > 1 ? "s" : ""}</span><strong>{alerts.length}</strong><small>alertes actives</small></div></header><div className="alerts-layout"><section className="alerts-list-card"><div className="section-title"><div className="alert-filters">
  <label htmlFor="severity-filter">Filtrer par niveau :</label>

  <select
    id="severity-filter"
    value={severityFilter}
    onChange={(e) =>
      setSeverityFilter(
        e.target.value as "all" | "info" | "warning" | "critical"
      )
    }
  >
    <option value="all">Tous les niveaux</option>
    <option value="info">{severityLabel.info}</option>
    <option value="warning">{severityLabel.warning}</option>
    <option value="critical">{severityLabel.critical}</option>
  </select>

  <label htmlFor="sort-order">Trier par date :</label>

  <select
    id="sort-order"
    value={sortOrder}
    onChange={(e) =>
      setSortOrder(e.target.value as "asc" | "desc")
    }
  >
    <option value="desc">Ordre décroissant (plus récentes)</option>
    <option value="asc">Ordre croissant (plus anciennes)</option>
  </select>
</div><div><span className="section-kicker">En cours</span><h2>Alertes actives</h2></div>{unread > 0 && <button type="button" className="read-all" onClick={onReadAll}><Check size={15} /> Tout marquer consulté</button>}</div>{alerts.length ? filteredAlerts.map((alert) => {
    const isRead = readIds.includes(alert.id); const isOpen = openAlert === alert.id;
    return <article className={`alert-item severity-${alert.severity} ${isRead ? "is-read" : "is-unread"} ${isOpen ? "is-open" : ""}`} key={alert.id}><button type="button" className="alert-trigger" aria-expanded={isOpen} onClick={() => { setOpenAlert(isOpen ? null : alert.id); onRead(alert.id); }}><span className="alert-icon"><AlertTriangle size={19} /></span><span className="alert-copy"><span className="alert-title"><strong>{alert.zone_name}</strong>{isRead ? <em><Check size={12} /> Consultée</em> : <em className="new-alert"><Eye size={12} /> Nouvelle</em>}</span><span>{alert.message}</span><small>{new Intl.DateTimeFormat("fr-CA", { dateStyle: "medium", timeStyle: "medium" }).format(new Date(alert.created_at))}</small></span><ChevronDown className="alert-chevron" size={18} /></button>{isOpen && <div className="alert-details"><div><span>Niveau</span><strong>{severityLabel[alert.severity]}</strong></div><div><span>Règle déclenchée</span><strong>{alert.code}</strong></div><div><span>État</span><strong>Active</strong></div><button type="button" onClick={() => setRuleZone(zones.find((item) => item.id === alert.zone)?.code || ruleZone)}>Voir les seuils de cet espace</button></div>}</article>;
  }) : <div className="empty-state"><CheckCircle2 size={28} /><strong>Aucune alerte active</strong></div>}</section><section className="rules-card"><div className="section-title"><div><span className="section-kicker">Configuration réelle</span><h2>Base des règles</h2></div></div><label className="rule-select">Espace</label>{profile ? <><div className={`rules-enabled ${profile.enabled ? "enabled" : "disabled"}`}>{profile.enabled ? "Seuils activés pour cet espace" : "Seuils désactivés pour cet espace"}</div><div className="rule-grid"><div><span>Température</span><strong>{profile.temperature_min} à {profile.temperature_max} °C</strong></div><div><span>Humidité</span><strong>{profile.humidity_min} à {profile.humidity_max} %</strong></div><div><span>Niveau sonore</span><strong>Avertissement {profile.sound_warning} · Critique {profile.sound_critical} dB</strong></div></div><h3>Contrôle de cohérence</h3><div className="rule-grid compact"><div><span>Variation température</span><strong>{profile.max_temperature_delta_per_minute} °C/min</strong></div><div><span>Variation humidité</span><strong>{profile.max_humidity_delta_per_minute} %/min</strong></div><div><span>Valeur inchangée</span><strong>{profile.stuck_after_minutes} min</strong></div></div></> : <p>Aucun profil de seuil n’est associé à cet espace.</p>}<div className="rules-note"><strong>Limites physiques utilisées par le serveur</strong><span>Une valeur hors limites est invalide. Une variation supérieure à la limite configurée ou une valeur inchangée trop longtemps est suspecte. L’alerte est résolue automatiquement quand une nouvelle mesure redevient normale.</span></div></section></div></main>;
}

export default function App() {
  const [page, setPage] = useState<Page>(() => pageFromPath(window.location.pathname)); const [zones, setZones] = useState<Zone[]>([]); const [observations, setObservations] = useState<Observation[]>([]); const [alerts, setAlerts] = useState<Alert[]>([]); const [historyZone, setHistoryZone] = useState<string | null>(null); const [status, setStatus] = useState<RealtimeStatus>("connecting"); const [loading, setLoading] = useState(true); const [error, setError] = useState<string | null>(null); const [lastUpdate, setLastUpdate] = useState<Date | null>(null); const [readAlertIds, setReadAlertIds] = useState<number[]>(() => { try { const saved = JSON.parse(localStorage.getItem(READ_ALERTS_KEY) || "[]"); return Array.isArray(saved) ? saved.filter((value): value is number => typeof value === "number") : []; } catch { return []; } }); const reconnectRef = useRef<number | null>(null);
  const refresh = useCallback(async () => { try { setError(null); const data = await loadDashboard(); setZones(data.zones); setObservations(data.observations); setAlerts(data.alerts); const newest = data.observations.map((item) => new Date(observationTime(item)).getTime()).filter(Number.isFinite).sort((a, b) => b - a)[0]; setLastUpdate(newest ? new Date(newest) : null); } catch (reason) { setError(reason instanceof Error ? reason.message : "Impossible de charger les données."); } finally { setLoading(false); } }, []);
  useEffect(() => { void refresh(); const interval = window.setInterval(() => void refresh(), 60_000); return () => window.clearInterval(interval); }, [refresh]);
  useEffect(() => { const handlePopState = () => setPage(pageFromPath(window.location.pathname)); window.addEventListener("popstate", handlePopState); return () => window.removeEventListener("popstate", handlePopState); }, []);
  // useEffect(() => { const interval = window.setInterval(() => { void Promise.all([loadLatestObservations(), loadActiveAlerts()]).then(([data, activeAlerts]) => { setObservations(data); setAlerts(activeAlerts); const newest = data.map((item) => new Date(observationTime(item)).getTime()).filter(Number.isFinite).sort((a, b) => b - a)[0]; if (newest) setLastUpdate(new Date(newest)); }).catch(() => undefined); }, 5000_000); return () => window.clearInterval(interval); }, []);
  useEffect(() => { let socket: WebSocket | null = null; let stopped = false; const connect = () => { if (stopped) return; setStatus("connecting"); const scheme = window.location.protocol === "https:" ? "wss" : "ws"; socket = new WebSocket(`${scheme}://${window.location.host}/ws/dashboard/`); socket.onopen = () => setStatus("connected"); socket.onmessage = (event) => { const message = JSON.parse(event.data) as { event: string; data?: Observation }; if (message.event === "observation.created" && message.data) { setObservations((current) => [message.data!, ...current].slice(0, 1000)); setLastUpdate(new Date(observationTime(message.data))); } }; socket.onerror = () => setStatus("disconnected"); socket.onclose = () => { setStatus("disconnected"); if (!stopped) reconnectRef.current = window.setTimeout(connect, 3000); }; }; connect(); return () => { stopped = true; if (reconnectRef.current) window.clearTimeout(reconnectRef.current); socket?.close(); }; }, []);
  const latest = useMemo(() => latestByZone(observations, zones), [observations, zones]); const unreadAlerts = alerts.filter((alert) => !readAlertIds.includes(alert.id)).length;
  const navigate = (nextPage: Page) => { setPage(nextPage); window.history.pushState({}, "", PAGE_PATHS[nextPage]); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const markAlertRead = (id: number) => { setReadAlertIds((current) => { if (current.includes(id)) return current; const next = [...current, id]; localStorage.setItem(READ_ALERTS_KEY, JSON.stringify(next)); return next; }); };
  const markAllAlertsRead = () => { const next = Array.from(new Set([...readAlertIds, ...alerts.map((alert) => alert.id)])); setReadAlertIds(next); localStorage.setItem(READ_ALERTS_KEY, JSON.stringify(next)); };
  const openHistory = (code: string) => { setHistoryZone(code); navigate("history"); };
  const averageFor = (type: MetricType) => { const values = zones.map((zone) => latest.get(`${zone.code}:${type}`)?.value).filter((value): value is number => value != null); return { value: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null, count: values.length }; };
  const temperature = averageFor("temperature"); const humidity = averageFor("humidity"); const sound_level = averageFor("sound_level"); const occupancy = averageFor("occupancy")
  return <div className="app-shell"><header className="topbar"><button className="brand" type="button" onClick={() => navigate("overview")}><span className="brand-mark"><Leaf size={22} /></span><span><strong>GRIDD</strong><small>Smart environment</small></span></button><nav className="top-nav" aria-label="Navigation principale"><button className={page === "overview" ? "active" : ""} type="button" onClick={() => navigate("overview")}>Vue d’ensemble</button><button className={page === "spaces" ? "active" : ""} type="button" onClick={() => navigate("spaces")}>Espaces</button><button className={page === "history" ? "active" : ""} type="button" onClick={() => navigate("history")}>Analyse historique</button><button className={page === "alerts" ? "active" : ""} type="button" onClick={() => navigate("alerts")}>Alertes{unreadAlerts > 0 && <span className="nav-badge">+{unreadAlerts}</span>}</button></nav><div className="topbar-actions"><StatusPill status={status} /><button className="icon-button" type="button" onClick={() => void refresh()} aria-label="Rafraîchir"><RefreshCw size={18} /></button></div></header>{error && <div className="global-error"><AlertTriangle size={17} />{error}</div>}{page === "overview" && <main className="dashboard"><header className="overview-head"><div><span className="overline"><Activity size={15} /> Vue d’ensemble</span><h1>État environnemental du GRIDD</h1><p>Synthèse des dernières mesures reçues.</p></div><div className="overview-context"><span>ÉTS · Pavillon A · A-1540</span><strong>{formatDate(new Date())}</strong><small>Dernière mesure : {lastUpdate ? formatTime(lastUpdate.toISOString()) : "—"}</small></div></header><section className="summary-grid three-columns"><SummaryCard label="Espaces suivis" value={String(6)} detail="zones actives" icon={Building2} tone="green" /><SummaryCard label="Température moyenne" value={temperature.value == null ? "—" : `${formatValue(temperature.value, "temperature")} °C`} detail={`${temperature.count}/${6} espaces avec mesure`} icon={Thermometer} tone="amber" /><SummaryCard label="Humidité moyenne" value={humidity.value == null ? "—" : `${formatValue(humidity.value, "humidity")} %`} detail={`${humidity.count}/${6} espaces avec mesure`} icon={Droplets} tone="blue" /><SummaryCard label="Niveau de son moyenne" value={sound_level.value == null ? "—" : `${formatValue(sound_level.value, "sound_level")} dB`} detail={`${sound_level.count}/${4} espaces avec mesure`} icon={Volume2} tone="purple" /><SummaryCard label="Nombre de personnes dans le GRIDD" value={occupancy.value == null ? "—" : `${formatValue(occupancy.value, "occupancy")}`} detail={`${occupancy.count}/${1} espaces avec mesure`} icon={Users} tone="red" /><SummaryCard label="Indice de confort thermique" value={temperature.value == null || humidity.value == null ? "—" : `${Math.round((0.7*(100-10*(Math.abs(temperature.value-25)))+0.3*(100-2*(Math.abs(humidity.value-35))))*10)/10}`} detail={`${temperature.count}/${6} espaces avec mesure`} icon={Thermometer} tone="blue" /><SummaryCard label="Taux d'occupation" value={occupancy.value == null ? "—" : `${Math.round((occupancy.value/30)*100*10)/10}`} detail={`${occupancy.count}/${1} espaces avec mesure`} icon={Users} tone="red" /><SummaryCard label="Indice de confort sonore" value={sound_level.value == null ? "—" : `${Math.round(Math.min(100,100-(100/50)*(sound_level.value-30))*10)/10}`} detail={`${sound_level.count}/${4} espaces avec mesure`} icon={Volume2} tone="purple" /></section><section className="availability-card"><div><span className="section-kicker">Mesures reçues</span><h2>Disponibilité par type de mesure</h2></div><div className="availability-grid">{METRIC_ORDER.map((type) => { const count = zones.filter((zone) => latest.has(`${zone.code}:${type}`)).length; const Icon = METRICS[type].icon; return <div key={type}><Icon size={18} style={{ color: METRICS[type].color }} /><span>{METRICS[type].label}</span><strong>{count}/{METRICS[type].label==="Niveau sonore" ? 4 : METRICS[type].label==="Occupation" ? 1 : 6}</strong></div>; })}</div></section></main>}{page === "spaces" && <SpacesView zones={zones} latest={latest} alerts={alerts} loading={loading} onHistory={openHistory} />}{page === "history" && <HistoryView zones={zones} latest={latest} initialZone={historyZone} />}{page === "alerts" && <AlertsView alerts={alerts} zones={zones} readIds={readAlertIds} onRead={markAlertRead} onReadAll={markAllAlertsRead} />}</div>;
}
