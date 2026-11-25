

class ObservationPersistenceService:
    """Enregistre les observations validées (avec leur zone et leur capteur)
    puis publie ``observation.persisted`` pour les modules en aval.

    Publie aussi ``zones.changed`` lorsqu'une zone ou un capteur apparaît, qu'un
    capteur change de zone (ou qu'une zone est renommée) : les tableaux de bord reçoivent alors la
    nouvelle liste des zones et de leurs mesures sans la redemander.

    Débit : ``persist_many`` enregistre un lot en une transaction (recherche
    des doublons + insertion groupée). Avec Kafka, les zones et capteurs déjà
    vus sont gardés en mémoire (``cache_references``) : plus de lecture de la
    zone, du profil et du capteur à chaque mesure. Avant, ~6 allers-retours
    avec PostgreSQL par mesure limitaient le module à ~40 mesures/s, et un
    rattrapage retardait aussi les zones à jour.
    """

    MAX_REFERENCES = 10_000

    def __init__(self, *, unit_of_work, zone_writer, sensor_writer, observation_writer, mapper, producer, cache_references=False):
        self._unit_of_work = unit_of_work
        self._zone_writer = zone_writer
        self._sensor_writer = sensor_writer
        self._observation_writer = observation_writer
        self._mapper = mapper
        self._producer = producer
        self._cache_references = cache_references
        self._zones = {}
        self._sensors = {}

    def persist(self, payload):
        created = self.persist_many([payload])
        return created[0] if created else None

    def persist_many(self, payloads):
        if not payloads:
            return []
        changed_zones = []
        try:
            with self._unit_of_work.atomic():
                items = []
                for payload in payloads:
                    zone, zone_changed = self._zone(payload["zone"])
                    sensor, sensor_changed = self._sensor(payload, zone)
                    if (zone_changed or sensor_changed) and zone.code not in changed_zones:
                        changed_zones.append(zone.code)
                    items.append((payload, zone, sensor))
                created = self._observation_writer.create_many(items)
        except Exception:
            # Une zone ou un capteur gardé en mémoire peut ne pas avoir été
            # enregistré (transaction annulée) ou avoir été supprimé : on relit.
            self.forget_references()
            raise

        # Publication après validation de la transaction : les modules en aval
        # ne reçoivent que des données réellement enregistrées.
        for zone_code in changed_zones:
            self._producer.zones_changed(zone_code)
        for observation in created:
            self._producer.observation_persisted(self._mapper.to_payload(observation))
        return created

    def forget_references(self):
        self._zones.clear()
        self._sensors.clear()

    def _zone(self, info):
        key = (info["code"], info.get("name"), info.get("type"))
        zone = self._zones.get(key) if self._cache_references else None
        if zone is not None:
            return zone, False
        zone, changed = self._zone_writer.upsert(info["code"], info.get("name"), info.get("type"))
        self._remember(self._zones, key, zone)
        return zone, changed

    def _sensor(self, payload, zone):
        metadata = payload.get("sensor_metadata") or {}
        key = (payload["node_id"], payload["metric"])
        cached = self._sensors.get(key) if self._cache_references else None
        stable = self._sensor_writer.stable_metadata(metadata)
        if cached is not None and cached[1] == stable and cached[0].zone_id == zone.pk:
            return cached[0], False
        sensor, created = self._sensor_writer.upsert(
            node_id=payload["node_id"], metric=payload["metric"], unit=payload["unit"], zone=zone, metadata=metadata
        )
        self._remember(self._sensors, key, (sensor, stable))
        return sensor, created

    def _remember(self, store, key, value):
        if not self._cache_references:
            return
        if len(store) >= self.MAX_REFERENCES:
            store.clear()
        store[key] = value
