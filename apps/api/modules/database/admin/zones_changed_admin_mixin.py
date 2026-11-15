import logging

from django.db import transaction

from modules.database.producers.database_events_producer import DatabaseEventsProducer
from shared.messaging import Messaging

logger = logging.getLogger(__name__)


class ZonesChangedAdminMixin:
    """Publie ``zones.changed`` après une modification faite dans l'admin
    (zone activée / renommée, capteur ajouté ou désactivé…) : les tableaux de
    bord reçoivent la nouvelle liste par WebSocket, sans la redemander.

    La publication a lieu après validation de la transaction ; un bus
    indisponible n'empêche pas l'enregistrement (journalisé seulement).
    """

    def save_related(self, request, form, formsets, change):
        # Appelé après save_model : la zone et ses lignes liées sont enregistrées.
        super().save_related(request, form, formsets, change)
        self._notify_zones_changed()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        self._notify_zones_changed()

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        self._notify_zones_changed()

    @staticmethod
    def _notify_zones_changed():
        def publish():
            try:
                DatabaseEventsProducer(Messaging.current().publisher()).zones_changed()
            except Exception:
                logger.exception("Impossible de publier zones.changed.")

        transaction.on_commit(publish)
