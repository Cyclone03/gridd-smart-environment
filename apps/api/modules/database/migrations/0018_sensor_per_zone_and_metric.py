"""Un capteur par zone et par type de mesure.

Avant : un capteur par nœud GRIDD (``environmental-node03``…). Quand GRIDD
déplaçait ou réétiquetait un nœud, ses mesures étaient rejetées (« zone
incohérente ») ou attribuées au mauvais espace.

Après : le capteur est identifié par ``<zone>-<mesure>`` (même convention que
``seed_gridd``). Chaque observation est rattachée au capteur de **sa propre
zone** (celle enregistrée avec la mesure), le nœud d'origine est conservé dans
``metadata.source_node_id``, puis les anciens capteurs par nœud sont supprimés.
Aucune observation n'est supprimée ni déplacée d'espace.
"""

from django.db import migrations


def sensor_key(zone_code, metric):
    # Copie volontaire de shared.kernel.sensor_identity.sensor_key : une
    # migration ne doit pas dépendre du code applicatif, qui peut évoluer.
    return f"{zone_code}-{metric}"


def per_zone_sensors(apps, schema_editor):
    Sensor = apps.get_model("core", "Sensor")
    Observation = apps.get_model("core", "Observation")
    Zone = apps.get_model("core", "Zone")
    zones = {zone.pk: zone for zone in Zone.objects.all()}

    for old in list(Sensor.objects.all()):
        if old.node_id == sensor_key(zones[old.zone_id].code, old.sensor_type):
            continue
        zone_ids = set(Observation.objects.filter(sensor_id=old.pk).values_list("zone_id", flat=True).distinct())
        zone_ids.add(old.zone_id)
        for zone_id in sorted(zone_ids):
            zone = zones[zone_id]
            metadata = dict(old.metadata) if isinstance(old.metadata, dict) else {}
            metadata["source_node_id"] = old.node_id
            target, created = Sensor.objects.get_or_create(
                node_id=sensor_key(zone.code, old.sensor_type),
                sensor_type=old.sensor_type,
                defaults={
                    "label": f"{zone.name} — {old.sensor_type}",
                    "zone_id": zone.pk,
                    "unit": old.unit,
                    "metadata": metadata,
                    "active": old.active,
                },
            )
            # Un capteur de démonstration désactivé reprend du service s'il
            # remplace un capteur réel actif.
            if not created and old.active and not target.active:
                target.active = True
                target.metadata = metadata
                target.save(update_fields=["active", "metadata"])
            Observation.objects.filter(sensor_id=old.pk, zone_id=zone_id).update(sensor_id=target.pk)
        old.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0017_weather_snapshot"),
    ]

    operations = [
        migrations.RunPython(per_zone_sensors, migrations.RunPython.noop),
    ]
