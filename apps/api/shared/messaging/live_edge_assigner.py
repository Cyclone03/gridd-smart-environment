from confluent_kafka import OFFSET_END


class LiveEdgeAssigner:
    """Callback ``on_assign`` : ignore l'arriéré validé et ne lit que les
    messages publiés après le démarrage (temps réel des capteurs)."""

    def __call__(self, consumer, partitions):
        for partition in partitions:
            partition.offset = OFFSET_END
        consumer.assign(partitions)
