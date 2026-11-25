import asyncio
import logging
import threading

from asgiref.sync import async_to_sync
from channels.layers import InMemoryChannelLayer, get_channel_layer

from modules.realtime.core.domain.realtime_groups import RealtimeGroups

logger = logging.getLogger(__name__)


class RealtimeBroadcaster:
    """Diffusion vers les navigateurs connectés (Django Channels) : adaptateur
    du port ``Broadcaster``.

    Les messages portent les données elles-mêmes (observation, alertes,
    zones) : les navigateurs n'ont aucune requête HTTP à refaire.

    Avec Redis, tous les envois passent par **une boucle asyncio persistante**
    (un thread dédié) : ``channels_redis`` garde ses connexions par boucle, et
    ``async_to_sync`` créait une boucle — donc une nouvelle connexion Redis —
    à chaque envoi (≈ 7 par lot de mesures). Pendant un rattrapage, ces
    dizaines de connexions par seconde saturaient Redis et bloquaient
    l'inscription des WebSocket côté API.

    Une panne du channel layer (Redis indisponible ou lent) est journalisée
    puis ignorée : la donnée est déjà enregistrée et un rejeu Kafka
    n'apporterait rien.
    """

    SEND_TIMEOUT_SECONDS = 5.0

    _loop = None
    _loop_lock = threading.Lock()

    def observation_created(self, payload):
        self._send(
            [
                (RealtimeGroups.DASHBOARD, {"type": "observation.created", "payload": payload}),
                (RealtimeGroups.zone(payload["zone_code"]), {"type": "observation.created", "payload": payload}),
            ],
            "observation.created",
        )

    def climate_prediction_created(self, payload):
        """Diffuse la prédiction au tableau de bord et à sa seule zone."""
        self._send(
            [RealtimeGroups.DASHBOARD, RealtimeGroups.zone(payload["zone_code"])],
            {"type": "climate_prediction.created", "payload": payload},
        )

    def weather_snapshot_created(self, payload):
        """Diffuse l'instantané météo commun à tous les espaces."""
        self._send(
            [RealtimeGroups.DASHBOARD],
            {"type": "weather_snapshot.created", "payload": payload},
        )

    def observations_created(self, payloads):
        """Un seul message par groupe pour un lot de mesures (au lieu d'un par mesure)."""
        if not payloads:
            return
        sends = [(RealtimeGroups.DASHBOARD, {"type": "observations.created", "payload": payloads})]
        by_zone = {}
        for payload in payloads:
            by_zone.setdefault(payload["zone_code"], []).append(payload)
        for zone_code, items in by_zone.items():
            sends.append((RealtimeGroups.zone(zone_code), {"type": "observations.created", "payload": items}))
        self._send(sends, "observations.created")

    def alerts_changed(self, payload):
        self._send([(RealtimeGroups.DASHBOARD, {"type": "alerts.changed", "payload": payload})], "alerts.changed")

    def zones_changed(self, payload):
        self._send([(RealtimeGroups.DASHBOARD, {"type": "zones.changed", "payload": payload})], "zones.changed")

    def _send(self, sends, label):
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning("Aucun channel layer configuré : événement %s non diffusé.", label)
            return

        async def deliver():
            for group, event in sends:
                await channel_layer.group_send(group, event)

        try:
            if isinstance(channel_layer, InMemoryChannelLayer):
                # Développement sans Redis : même processus, pas de connexion à réutiliser.
                async_to_sync(deliver)()
                return
            future = asyncio.run_coroutine_threadsafe(deliver(), self._event_loop())
            try:
                future.result(timeout=self.SEND_TIMEOUT_SECONDS)
            except TimeoutError:
                future.cancel()
                logger.warning("Diffusion %s abandonnée : Redis ne répond pas en %ss.", label, self.SEND_TIMEOUT_SECONDS)
        except Exception:
            logger.exception("Impossible de diffuser l'événement %s.", label)

    @classmethod
    def _event_loop(cls):
        with cls._loop_lock:
            if cls._loop is None or cls._loop.is_closed():
                loop = asyncio.new_event_loop()
                threading.Thread(target=loop.run_forever, name="gridd-realtime-broadcast", daemon=True).start()
                cls._loop = loop
        return cls._loop
