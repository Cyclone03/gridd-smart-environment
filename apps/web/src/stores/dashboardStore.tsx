/**
 * Données partagées par toutes les vues : zones, dernières mesures, alertes
 * actives, état du temps réel et alertes déjà consultées.
 *
 * Sources : chargement initial + rafraîchissement périodique (filet de
 * sécurité), complétés par le WebSocket (nouvelles mesures, changements
 * d'alertes).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { DASHBOARD_REFRESH_MS, MAX_LIVE_OBSERVATIONS, STORAGE_KEYS } from "../constants/app";
import { errorMessage } from "../requests/httpClient";
import type { Alert } from "../resources/alert";
import type { Observation } from "../resources/observation";
import type { Zone } from "../resources/zone";
import { listActiveAlerts } from "../services/alertsService";
import { getLatestObservations } from "../services/observationsService";
import { subscribeToDashboard } from "../services/realtimeService";
import { listZones } from "../services/zonesService";
import type { RealtimeStatus } from "../types/common";
import {
  latestByZone,
  newestTimestamp,
  observationTime,
  visibleZones,
  type LatestReadings,
} from "../utils/observations";
import { readStorage, writeStorage } from "../utils/storage";

interface DashboardContextValue {
  /** Zones affichées (hors zones masquées). */
  zones: Zone[];
  latest: LatestReadings;
  alerts: Alert[];
  status: RealtimeStatus;
  loading: boolean;
  error: string | null;
  lastUpdate: Date | null;
  refresh: () => Promise<void>;
  readAlertIds: number[];
  unreadAlertCount: number;
  markAlertRead: (id: number) => void;
  markAllAlertsRead: () => void;
}

const DashboardContext = createContext<DashboardContextValue | null>(null);

function loadReadIds(): number[] {
  try {
    const saved: unknown = JSON.parse(readStorage(STORAGE_KEYS.readAlerts) || "[]");
    return Array.isArray(saved) ? saved.filter((value): value is number => typeof value === "number") : [];
  } catch {
    return [];
  }
}

export function DashboardProvider({ children, realtime = true }: { children: ReactNode; realtime?: boolean }) {
  const [zones, setZones] = useState<Zone[]>([]);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [status, setStatus] = useState<RealtimeStatus>("connecting");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [readAlertIds, setReadAlertIds] = useState<number[]>(loadReadIds);

  const refresh = useCallback(async () => {
    try {
      const [zoneList, latestObservations, activeAlerts] = await Promise.all([
        listZones(),
        getLatestObservations(),
        listActiveAlerts(),
      ]);
      setZones(zoneList);
      setObservations(latestObservations);
      setAlerts(activeAlerts);
      setLastUpdate(newestTimestamp(latestObservations));
      setError(null);
    } catch (reason) {
      setError(errorMessage(reason, "Impossible de charger les données."));
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshAlerts = useCallback(() => {
    listActiveAlerts()
      .then(setAlerts)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => void refresh(), DASHBOARD_REFRESH_MS);
    return () => window.clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    if (!realtime) return;
    return subscribeToDashboard({
      onStatus: setStatus,
      onAlertsChanged: refreshAlerts,
      onObservation: (observation) => {
        setObservations((current) => [observation, ...current].slice(0, MAX_LIVE_OBSERVATIONS));
        setLastUpdate(new Date(observationTime(observation)));
      },
    });
  }, [realtime, refreshAlerts]);

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

  const value = useMemo<DashboardContextValue>(() => {
    const shownZones = visibleZones(zones);
    return {
      zones: shownZones,
      latest: latestByZone(observations, zones),
      alerts,
      status,
      loading,
      error,
      lastUpdate,
      refresh,
      readAlertIds,
      unreadAlertCount: alerts.filter((alert) => !readAlertIds.includes(alert.id)).length,
      markAlertRead,
      markAllAlertsRead,
    };
  }, [
    zones,
    observations,
    alerts,
    status,
    loading,
    error,
    lastUpdate,
    refresh,
    readAlertIds,
    markAlertRead,
    markAllAlertsRead,
  ]);

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard(): DashboardContextValue {
  const context = useContext(DashboardContext);
  if (!context) throw new Error("useDashboard doit être utilisé dans <DashboardProvider>.");
  return context;
}
