/**
 * Données partagées par toutes les vues : zones, dernières mesures, alertes
 * (actives et historique récent), état du temps réel et alertes consultées.
 *
 * Source unique : le WebSocket `/ws/dashboard/`. À chaque (re)connexion le
 * serveur envoie un instantané complet, puis les changements (mesures,
 * alertes, zones) avec leurs données. Aucune requête HTTP n'est faite pour
 * ces données, ni au chargement ni à intervalle régulier.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ALERT_HISTORY_DAYS } from "../constants/alerts";
import { REALTIME_BATCH_MS, STORAGE_KEYS } from "../constants/app";
import type { Alert } from "../resources/alert";
import type { Observation } from "../resources/observation";
import type { AlertsState } from "../resources/realtime";
import type { Zone } from "../resources/zone";
import { subscribeToDashboard, type DashboardConnection } from "../services/realtimeService";
import type { RealtimeStatus } from "../types/common";
import { latestByZone, mergeLatest, newestTimestamp, visibleZones, type LatestReadings } from "../utils/observations";
import { readStorage, writeStorage } from "../utils/storage";

/** Reçoit les nouvelles mesures (par lots) : graphiques mis à jour en direct. */
export type ObservationListener = (observations: Observation[]) => void;

interface DashboardContextValue {
  /** Zones affichées (hors zones masquées). */
  zones: Zone[];
  latest: LatestReadings;
  /** Alertes actives. */
  alerts: Alert[];
  /** Alertes résolues récentes (page Alertes). */
  alertHistory: Alert[];
  alertHistoryDays: number;
  status: RealtimeStatus;
  /** Vrai tant que le premier instantané n'a pas été reçu. */
  loading: boolean;
  error: string | null;
  lastUpdate: Date | null;
  /** Redemande l'instantané complet au serveur (par le WebSocket). */
  refresh: () => void;
  subscribeObservations: (listener: ObservationListener) => () => void;
  readAlertIds: number[];
  unreadAlertCount: number;
  markAlertRead: (id: number) => void;
  markAllAlertsRead: () => void;
}

const DashboardContext = createContext<DashboardContextValue | null>(null);

const CONNECTION_ERROR = "Connexion temps réel au serveur GRIDD impossible. Nouvelle tentative automatique…";

function loadReadIds(): number[] {
  try {
    const saved: unknown = JSON.parse(readStorage(STORAGE_KEYS.readAlerts) || "[]");
    return Array.isArray(saved) ? saved.filter((value): value is number => typeof value === "number") : [];
  } catch {
    return [];
  }
}

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [zones, setZones] = useState<Zone[]>([]);
  const [latest, setLatest] = useState<LatestReadings>(() => new Map());
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertHistory, setAlertHistory] = useState<Alert[]>([]);
  const [alertHistoryDays, setAlertHistoryDays] = useState(ALERT_HISTORY_DAYS);
  const [status, setStatus] = useState<RealtimeStatus>("connecting");
  const [synced, setSynced] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [readAlertIds, setReadAlertIds] = useState<number[]>(loadReadIds);

  const connectionRef = useRef<DashboardConnection | null>(null);
  const listenersRef = useRef(new Set<ObservationListener>());
  const zonesRef = useRef<Zone[]>([]);
  zonesRef.current = zones;

  useEffect(() => {
    let pending: Observation[] = [];
    let flushTimer: ReturnType<typeof setTimeout> | null = null;

    const touch = (date: Date | null) => {
      if (date) setLastUpdate((current) => (current && current >= date ? current : date));
    };
    const applyAlerts = (state: AlertsState) => {
      setAlerts(state.active);
      setAlertHistory(state.history);
      if (state.history_days) setAlertHistoryDays(state.history_days);
    };
    const flush = () => {
      flushTimer = null;
      const batch = pending;
      pending = [];
      if (!batch.length) return;
      setLatest((current) => mergeLatest(current, batch, zonesRef.current));
      touch(newestTimestamp(batch));
      listenersRef.current.forEach((listener) => listener(batch));
    };

    const connection = subscribeToDashboard({
      onStatus: setStatus,
      onSnapshot: (snapshot) => {
        zonesRef.current = snapshot.zones;
        setZones(snapshot.zones);
        setLatest(latestByZone(snapshot.latest, snapshot.zones));
        applyAlerts(snapshot.alerts);
        setLastUpdate(newestTimestamp(snapshot.latest));
        setServerError(null);
        setSynced(true);
      },
      onObservation: (observation) => {
        pending.push(observation);
        flushTimer ??= setTimeout(flush, REALTIME_BATCH_MS);
      },
      onAlerts: applyAlerts,
      onZones: (next) => {
        zonesRef.current = next;
        setZones(next);
      },
      onServerError: setServerError,
    });
    connectionRef.current = connection;
    return () => {
      connection.close();
      connectionRef.current = null;
      if (flushTimer) clearTimeout(flushTimer);
    };
  }, []);

  const refresh = useCallback(() => {
    connectionRef.current?.requestSnapshot();
  }, []);

  const subscribeObservations = useCallback((listener: ObservationListener) => {
    listenersRef.current.add(listener);
    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  const persistReadIds = useCallback((ids: number[]) => {
    writeStorage(STORAGE_KEYS.readAlerts, JSON.stringify(ids));
    return ids;
  }, []);

  const markAlertRead = useCallback(
    (id: number) => setReadAlertIds((current) => (current.includes(id) ? current : persistReadIds([...current, id]))),
    [persistReadIds],
  );

  const markAllAlertsRead = useCallback(
    () =>
      setReadAlertIds((current) =>
        persistReadIds(Array.from(new Set([...current, ...alerts.map((alert) => alert.id)]))),
      ),
    [alerts, persistReadIds],
  );

  const shownZones = useMemo(() => visibleZones(zones), [zones]);
  const error = serverError ?? (!synced && status === "disconnected" ? CONNECTION_ERROR : null);

  const value = useMemo<DashboardContextValue>(
    () => ({
      zones: shownZones,
      latest,
      alerts,
      alertHistory,
      alertHistoryDays,
      status,
      loading: !synced,
      error,
      lastUpdate,
      refresh,
      subscribeObservations,
      readAlertIds,
      unreadAlertCount: alerts.filter((alert) => !readAlertIds.includes(alert.id)).length,
      markAlertRead,
      markAllAlertsRead,
    }),
    [
      shownZones,
      latest,
      alerts,
      alertHistory,
      alertHistoryDays,
      status,
      synced,
      error,
      lastUpdate,
      refresh,
      subscribeObservations,
      readAlertIds,
      markAlertRead,
      markAllAlertsRead,
    ],
  );

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard(): DashboardContextValue {
  const context = useContext(DashboardContext);
  if (!context) throw new Error("useDashboard doit être utilisé dans <DashboardProvider>.");
  return context;
}
