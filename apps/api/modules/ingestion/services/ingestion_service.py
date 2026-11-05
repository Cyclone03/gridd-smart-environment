from modules.ingestion.domain.past_reading import PastReading


class IngestionService:
    """Logique métier de l'ingestion d'une mesure capteur.

    1. rattachement à une zone (déduite des métadonnées du capteur) ;
    2. cohérence avec le capteur connu (zone, unité, activation) et le type ;
    3. contrôle de qualité (valeur impossible, capteur bloqué, variation rapide) ;
    4. publication de l'observation validée — sa persistance est assurée par
       le module Database.

    Lève ``MessageRejected`` pour une mesure à écarter.
    """

    def __init__(self, *, zone_resolver, sensors, validator, history, profiles, assessor, producer):
        self._zone_resolver = zone_resolver
        self._sensors = sensors
        self._validator = validator
        self._history = history
        self._profiles = profiles
        self._assessor = assessor
        self._producer = producer

    def ingest(self, reading) -> dict:
        zone = self._zone_resolver.resolve(reading.source_metadata, reading.node_id)
        value = self._validator.validate(reading, zone.code, self._sensors.find(reading.node_id, reading.metric))
        quality = self._assessor.assess(
            metric=reading.metric,
            value=value,
            observed_at=reading.observed_at,
            now=reading.received_at,
            history=self._history.recent(reading.node_id, reading.metric),
            profile=self._profiles.for_zone(zone.code),
        )

        payload = {
            "event_id": reading.event_id,
            "node_id": reading.node_id,
            "metric": reading.metric,
            "value": value,
            "unit": reading.unit,
            "observed_at": reading.observed_at.isoformat() if reading.observed_at else None,
            "received_at": reading.received_at.isoformat(),
            "metadata": reading.metadata,
            "sensor_metadata": reading.source_metadata,
            "quality_status": quality.status,
            "quality_reason": quality.reason,
            "zone": {"code": zone.code, "name": zone.name, "type": zone.zone_type},
        }
        self._producer.publish(payload)
        self._history.record(reading.node_id, reading.metric, PastReading(value, reading.observed_at, reading.received_at))
        return payload
