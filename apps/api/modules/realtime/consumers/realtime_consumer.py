import logging
from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from modules.realtime.services.dashboard_snapshot_service import DashboardSnapshotService
from modules.realtime.services.realtime_broadcaster import RealtimeBroadcaster
from shared.contracts.event_types import EventTypes
from shared.messaging import EventHandler

logger = logging.getLogger(__name__)


class RealtimeConsumer(EventHandler):
    """Relaie aux navigateurs les faits persistés par le module Database :
    les tableaux de bord ne reçoivent que des données réellement enregistrées.

    Pour ``alerts.changed`` et ``zones.changed``, la nouvelle liste est lue une
    seule fois ici puis diffusée à tous les navigateurs connectés (au lieu que
    chaque navigateur la redemande à l'API REST).
    """

    # Au-delà, une mesure relayée est un rattrapage et n'est pas diffusée une à une.
    LIVE_WINDOW = timedelta(minutes=2)

    def __init__(self, broadcaster, snapshots):
        self._broadcaster = broadcaster
        self._snapshots = snapshots
        # Pendant un lot Kafka : une seule relecture/diffusion par type à la fin.
        self._batching = False
        self._pending = set()
        self._observations = []

    @classmethod
    def build(cls):
        return cls(RealtimeBroadcaster(), DashboardSnapshotService())

    def routes(self):
        return {
            EventTypes.OBSERVATION_PERSISTED: lambda event: self._observation(event.payload),
            EventTypes.ALERTS_CHANGED: lambda event: self._changed("alerts"),
            EventTypes.ZONES_CHANGED: lambda event: self._changed("zones"),
        }

    def begin_batch(self):
        self._batching = True

    def end_batch(self):
        self._batching = False
        observations, self._observations = self._observations, []
        if observations:
            self._broadcaster.observations_created(self.coalesce(observations))
        pending, self._pending = self._pending, set()
        for kind in sorted(pending):
            self._broadcast(kind)

    def _observation(self, payload):
        if self._batching:
            self._observations.append(payload)
        else:
            self._broadcaster.observation_created(payload)

    @classmethod
    def coalesce(cls, observations, now=None):
        """Mesures à diffuser pour un lot.

        Les mesures récentes sont toutes gardées (graphiques en direct). Les
        anciennes (rattrapage d'un arriéré) sont réduites à la plus récente
        par capteur et par mesure : diffuser des milliers de valeurs passées
        saturait les files des navigateurs (« channels over capacity ») sans
        rien apporter à l'affichage.
        """
        limit = (now or timezone.now()) - cls.LIVE_WINDOW
        fresh, latest = [], {}
        for payload in observations:
            moment = parse_datetime(payload.get("observed_at") or payload.get("received_at") or "")
            if moment is not None and moment >= limit:
                fresh.append(payload)
                continue
            key = (payload.get("zone_code"), payload.get("sensor"), payload.get("type"))
            known = latest.get(key)
            if known is None or (payload.get("observed_at") or "") >= (known.get("observed_at") or ""):
                latest[key] = payload
        return [*latest.values(), *fresh]

    def _changed(self, kind):
        # Une rafale de changements (ex. 90 alerts.changed en 20 s) ne donne
        # qu'une lecture en base et une diffusion par lot.
        if self._batching:
            self._pending.add(kind)
        else:
            self._broadcast(kind)

    def _broadcast(self, kind):
        if kind == "alerts":
            self._relay(self._snapshots.alerts, self._broadcaster.alerts_changed)
        else:
            self._relay(self._snapshots.zones, self._broadcaster.zones_changed)

    @staticmethod
    def _relay(read, broadcast):
        try:
            payload = read()
        except Exception:
            # Base indisponible : les navigateurs se resynchroniseront à la
            # prochaine connexion (snapshot) ou au prochain changement.
            logger.exception("Lecture impossible pour la diffusion temps réel.")
            return
        broadcast(payload)
