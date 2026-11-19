/**
 * Données partagées par toutes les vues : zones, dernières mesures, prédictions,
 * alertes (actives et historique récent), état du temps réel et alertes consultées.
 *
 * Source unique : le WebSocket `/ws/dashboard/`. À chaque (re)connexion le
 * serveur envoie un instantané complet, puis les changements (mesures,
 * prédictions, alertes, zones) avec leurs données. Les dernières prédictions
 * persistées sont relues par REST au chargement et à chaque reconnexion.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ALERT_HISTORY_DAYS } from "../constants/alerts";
import { REALTIME_BATCH_MS, STORAGE_KEYS } from "../constants/app";
import { errorMessage, isAbortError } from "../requests/httpClient";
import type { Alert } from "../resources/alert";
import {
  mergeLatestClimatePredictions,
  type ClimatePrediction,
  type ClimatePredictionZoneCode,
} from "../resources/climatePrediction";
import type { Observation } from "../resources/observation";
import type { AlertsState } from "../resources/realtime";
import { mergeLatestWeatherSnapshot, type WeatherSnapshot } from "../resources/weatherSnapshot";
import type { Zone } from "../resources/zone";
import { fetchLatestClimatePredictions } from "../services/climatePredictionService";
import { fetchLatestWeatherSnapshot } from "../services/weatherSnapshotService";
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
  climatePredictions: ReadonlyMap<ClimatePredictionZoneCode, ClimatePrediction>;
  climatePredictionsLoading: boolean;
  climatePredictionsError: string | null;
  climatePredictionDataInvalid: boolean;
  weatherSnapshot: WeatherSnapshot | null;
  weatherSnapshotLoading: boolean;
  weatherSnapshotError: string | null;
  weatherSnapshotDataInvalid: boolean;
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
  const [climatePredictions, setClimatePredictions] = useState<
    ReadonlyMap<ClimatePredictionZoneCode, ClimatePrediction>
  >(() => new Map());
  const [climatePredictionsLoading, setClimatePredictionsLoading] = useState(true);
  const [climatePredictionsError, setClimatePredictionsError] = useState<string | null>(null);
  const [climatePredictionDataInvalid, setClimatePredictionDataInvalid] = useState(false);
  const [weatherSnapshot, setWeatherSnapshot] = useState<WeatherSnapshot | null>(null);
  const [weatherSnapshotLoading, setWeatherSnapshotLoading] = useState(true);
  const [weatherSnapshotError, setWeatherSnapshotError] = useState<string | null>(null);
  const [weatherSnapshotDataInvalid, setWeatherSnapshotDataInvalid] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertHistory, setAlertHistory] = useState<Alert[]>([]);
  const [alertHistoryDays, setAlertHistoryDays] = useState(ALERT_HISTORY_DAYS);
  const [status, setStatus] = useState<RealtimeStatus>("connecting");
  const [synced, setSynced] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [readAlertIds, setReadAlertIds] = useState<number[]>(loadReadIds);

  const connectionRef = useRef<DashboardConnection | null>(null);
  const refreshPredictionsRef = useRef<() => void>(() => {});
  const refreshWeatherRef = useRef<() => void>(() => {});
  const listenersRef = useRef(new Set<ObservationListener>());
  const zonesRef = useRef<Zone[]>([]);
  zonesRef.current = zones;

  useEffect(() => {
    let pending: Observation[] = [];
    let flushTimer: ReturnType<typeof setTimeout> | null = null;
    let active = true;
    let predictionRequest: AbortController | null = null;
    let weatherRequest: AbortController | null = null;
    let connectedOnce = false;

    const refreshPredictions = () => {
      predictionRequest?.abort();
      const controller = new AbortController();
      predictionRequest = controller;
      setClimatePredictionsLoading(true);
      void fetchLatestClimatePredictions(controller.signal)
        .then(({ predictions, invalidCount }) => {
          if (!active) return;
          setClimatePredictions((current) => mergeLatestClimatePredictions(current, predictions));
          setClimatePredictionDataInvalid(invalidCount > 0);
          setClimatePredictionsError(null);
        })
        .catch((error: unknown) => {
          if (!active || isAbortError(error)) return;
          setClimatePredictionsError(errorMessage(error, "Impossible de charger les prédictions climatiques."));
        })
        .finally(() => {
          if (!active || predictionRequest !== controller) return;
          predictionRequest = null;
          setClimatePredictionsLoading(false);
        });
    };
    refreshPredictionsRef.current = refreshPredictions;
    refreshPredictions();

    const refreshWeather = () => {
      weatherRequest?.abort();
      const controller = new AbortController();
      weatherRequest = controller;
      setWeatherSnapshotLoading(true);
      void fetchLatestWeatherSnapshot(controller.signal)
        .then((snapshot) => {
          if (!active) return;
          setWeatherSnapshot((current) => mergeLatestWeatherSnapshot(current, snapshot));
          setWeatherSnapshotDataInvalid(false);
          setWeatherSnapshotError(null);
        })
        .catch((error: unknown) => {
          if (!active || isAbortError(error)) return;
          setWeatherSnapshotError(errorMessage(error, "Impossible de charger la météo extérieure."));
        })
        .finally(() => {
          if (!active || weatherRequest !== controller) return;
          weatherRequest = null;
          setWeatherSnapshotLoading(false);
        });
    };
    refreshWeatherRef.current = refreshWeather;
    refreshWeather();

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
      onStatus: (nextStatus) => {
        setStatus(nextStatus);
        if (nextStatus === "connected") {
          if (connectedOnce) {
            refreshPredictions();
            refreshWeather();
          }
          connectedOnce = true;
        }
      },
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
      onClimatePrediction: (prediction) => {
        setClimatePredictions((current) => mergeLatestClimatePredictions(current, [prediction]));
        setClimatePredictionDataInvalid(false);
        setClimatePredictionsError(null);
      },
      onInvalidClimatePrediction: () => setClimatePredictionDataInvalid(true),
      onWeatherSnapshot: (snapshot) => {
        setWeatherSnapshot((current) => mergeLatestWeatherSnapshot(current, snapshot));
        setWeatherSnapshotDataInvalid(false);
        setWeatherSnapshotError(null);
      },
      onInvalidWeatherSnapshot: () => setWeatherSnapshotDataInvalid(true),
      onAlerts: applyAlerts,
      onZones: (next) => {
        zonesRef.current = next;
        setZones(next);
      },
      onServerError: setServerError,
    });
    connectionRef.current = connection;
    return () => {
      active = false;
      predictionRequest?.abort();
      weatherRequest?.abort();
      refreshPredictionsRef.current = () => {};
      refreshWeatherRef.current = () => {};
      connection.close();
      connectionRef.current = null;
      if (flushTimer) clearTimeout(flushTimer);
    };
  }, []);

  const refresh = useCallback(() => {
    connectionRef.current?.requestSnapshot();
    refreshPredictionsRef.current();
    refreshWeatherRef.current();
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
      climatePredictions,
      climatePredictionsLoading,
      climatePredictionsError,
      climatePredictionDataInvalid,
      weatherSnapshot,
      weatherSnapshotLoading,
      weatherSnapshotError,
      weatherSnapshotDataInvalid,
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
      climatePredictions,
      climatePredictionsLoading,
      climatePredictionsError,
      climatePredictionDataInvalid,
      weatherSnapshot,
      weatherSnapshotLoading,
      weatherSnapshotError,
      weatherSnapshotDataInvalid,
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
