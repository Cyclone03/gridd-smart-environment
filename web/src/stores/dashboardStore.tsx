/**
 * Données partagées par toutes les vues : zones, dernières mesures, alertes
 * actives, confort actuel des zones, état du temps réel et alertes déjà
 * consultées. `energyRevision` augmente à chaque nouvelle estimation
 * d'énergie : les vues concernées s'en servent pour se recharger.
 *
 * Sources : chargement initial + rafraîchissement périodique (filet de
 * sécurité), complétés par le WebSocket (nouvelles mesures, changements
 * d'alertes).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { DASHBOARD_REFRESH_MS, MAX_LIVE_OBSERVATIONS, STORAGE_KEYS } from "../constants/app";
import { errorMessage } from "../requests/httpClient";
import type { Alert } from "../resources/alert";
import { applyComfortUpdate, type ZoneComfort } from "../resources/comfort";
import type { Observation } from "../resources/observation";
import type { Zone } from "../resources/zone";
import { listActiveAlerts } from "../services/alertsService";
import { getCurrentComfort } from "../services/comfortService";
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
  /** Confort actuel des zones affichées. */
  comfort: ZoneComfort[];
  energyRevision: number;
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
  const [comfort, setComfort] = useState<ZoneComfort[]>([]);
  const [energyRevision, setEnergyRevision] = useState(0);
  const [status, setStatus] = useState<RealtimeStatus>("connecting");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [readAlertIds, setReadAlertIds] = useState<number[]>(loadReadIds);

  const refresh = useCallback(async () => {
    try {
      const [zoneList, latestObservations, activeAlerts, currentComfort] = await Promise.all([
        listZones(),
        getLatestObservations(),
        listActiveAlerts(),
        getCurrentComfort(),
      ]);
      setZones(zoneList);
      setObservations(latestObservations);
      setAlerts(activeAlerts);
      setComfort(currentComfort);
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
      onComfort: (update) => setComfort((current) => applyComfortUpdate(current, update)),
      onEnergy: () => setEnergyRevision((value) => value + 1),
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
    const shownCodes = new Set(shownZones.map((zone) => zone.code));
    return {
      zones: shownZones,
      latest: latestByZone(observations, zones),
      alerts,
      comfort: comfort.filter((zone) => shownCodes.has(zone.zone_code)),
      energyRevision,
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
    comfort,
    energyRevision,
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
