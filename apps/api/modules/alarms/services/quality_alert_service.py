from modules.alarms.domain.alert_codes import AlertCodes
from modules.database.models import Alert, Observation


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

        if status == Observation.QualityStatus.NORMAL:
            if self._store.is_active(zone_code, code):
                self._producer.alert_resolved(
                    zone_code=zone_code,
                    code=code,
                    resolution=Alert.Resolution.RETURNED_TO_NORMAL,
                )
                self._store.remember(zone_code, code, False)
            return

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
