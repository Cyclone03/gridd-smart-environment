class ObservationPayloadMapper:
    """Représentation d'une observation persistée, publiée dans
    ``observation.persisted`` (et relayée telle quelle aux navigateurs)."""

    def to_payload(self, observation) -> dict:
        return {
            "id": observation.pk,
            "zone": observation.zone_id,
            "zone_code": observation.zone.code,
            "zone_name": observation.zone.name,
            "sensor": observation.sensor_id,
            "sensor_node_id": observation.sensor.node_id,
            "type": observation.type,
            "value": observation.value,
            "unit": observation.unit,
            "observed_at": observation.observed_at.isoformat() if observation.observed_at else None,
            "received_at": observation.received_at.isoformat(),
            "quality_status": observation.quality_status,
            "quality_reason": observation.quality_reason,
            "metadata": observation.metadata,
        }
