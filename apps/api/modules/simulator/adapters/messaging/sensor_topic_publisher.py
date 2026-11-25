import json

from shared.contracts.topics import Topics


class SensorTopicPublisher:
    """Adaptateur du port ``ReadingPublisher`` : un message JSON brut sur le
    topic capteur du type de mesure (clé de partition : ``node_id``)."""

    def __init__(self, publisher):
        self._publisher = publisher

    def supports(self, metric) -> bool:
        return Topics.sensor_topic_for(metric) is not None

    def publish(self, metric, node_id, message) -> None:
        self._publisher.publish_raw(
            Topics.sensor_topic_for(metric),
            json.dumps(message).encode("utf-8"),
            key=node_id,
        )
