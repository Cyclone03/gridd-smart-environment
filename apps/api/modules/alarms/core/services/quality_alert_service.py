
from modules.alarms.core.domain.alert_codes import AlertCodes
from shared.kernel.timestamps import parse_datetime
from shared.kernel.vocabulary import AlertResolution, QualityStatus


class QualityAlertService:
    """Alertes de qualité des données (``DATA_QUALITY_<MESURE>``).

    Une mesure suspecte ou invalide ouvre (ou met à jour) l'alerte de sa zone ;
    une mesure normale la résout.
    """

    REFRESH_FIELDS = ("observation", "message", "severity")

    def __init__(self, *, store, producer, messages):
        self._store = store
        self._producer = producer
        self._messages = messages

    def process(self, observation):
        zone_code = observation["zone_code"]
        code = AlertCodes.for_quality(observation["type"])
        status = observation["quality_status"]

        if status == QualityStatus.NORMAL:
            if self._store.is_active(zone_code, code):
                self._producer.alert_resolved(
                    zone_code=zone_code,
                    code=code,
                    resolution=AlertResolution.RETURNED_TO_NORMAL,
                )
                self._store.remember(zone_code, code, False)
            return

        moment = parse_datetime(observation.get("observed_at") or observation["received_at"])
        if not self._store.should_refresh(zone_code, code, status, moment):
            return  # alerte déjà active et à jour : rien à republier
        self._producer.alert_raised(
            zone_code=zone_code,
            code=code,
            rule_id=None,
            severity=self._messages.quality_severity(status),
            message=self._messages.quality_message(status, observation["quality_reason"], observation["zone_name"]),
            trigger_value=observation["value"],
            observation_id=observation["id"],
            refresh_fields=self.REFRESH_FIELDS,
        )
        self._store.remember(zone_code, code, True)
