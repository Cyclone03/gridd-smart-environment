from modules.database.models import ThresholdProfile, Zone


class ZoneWriter:
    """Création et mise à jour des zones (et de leur profil de qualité)."""

    def upsert(self, code, name=None, zone_type=None) -> Zone:
        zone, _ = Zone.objects.get_or_create(
            code=code,
            defaults={"name": name or code, "zone_type": zone_type or Zone.ZoneType.OTHER},
        )
        changed_fields = []
        if name and zone.name != name:
            zone.name = name
            changed_fields.append("name")
        if zone_type and zone.zone_type != zone_type:
            zone.zone_type = zone_type
            changed_fields.append("zone_type")
        if changed_fields:
            zone.save(update_fields=changed_fields)

        # Toute zone possède un profil de qualité, désactivé par défaut.
        ThresholdProfile.objects.get_or_create(zone=zone, defaults={"enabled": False})
        return zone

    def find(self, code) -> Zone | None:
        return Zone.objects.filter(code=code).first()
