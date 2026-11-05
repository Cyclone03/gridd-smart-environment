from django.db import transaction


class ObservationPersistenceService:
    """Enregistre une observation validée (avec sa zone et son capteur) puis
    publie ``observation.persisted`` pour les modules en aval."""

    def __init__(self, *, zone_writer, sensor_writer, observation_writer, mapper, producer):
        self._zone_writer = zone_writer
        self._sensor_writer = sensor_writer
        self._observation_writer = observation_writer
        self._mapper = mapper
        self._producer = producer

    def persist(self, payload):
        zone_info = payload["zone"]
        with transaction.atomic():
            zone = self._zone_writer.upsert(zone_info["code"], zone_info.get("name"), zone_info.get("type"))
            sensor = self._sensor_writer.upsert(
                node_id=payload["node_id"],
                metric=payload["metric"],
                unit=payload["unit"],
                zone=zone,
                metadata=payload.get("sensor_metadata") or {},
            )
            observation, created = self._observation_writer.create(
                event_id=payload.get("event_id"),
                sensor=sensor,
                zone=zone,
                payload=payload,
            )
        # Publication après validation de la transaction : les modules en aval
        # ne reçoivent que des données réellement enregistrées.
        if created:
            self._producer.observation_persisted(self._mapper.to_payload(observation))
        return observation
