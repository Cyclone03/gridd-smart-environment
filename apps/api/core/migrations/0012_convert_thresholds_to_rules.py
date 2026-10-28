"""Conversion des seuils fixes de ThresholdProfile en règles d'alarme.

Avant la refonte, les alarmes de seuil étaient codées en dur :

- température hors de [temperature_min ; temperature_max] → avertissement ;
- humidité hors de [humidity_min ; humidity_max] → avertissement ;
- niveau sonore ≥ sound_warning → avertissement ;
- niveau sonore > sound_critical → critique ;
- seuils CO₂ : stockés mais jamais évalués (non convertis).

Chaque profil donne les règles équivalentes, actives seulement si le profil
l'était. Si tous les profils portent exactement les mêmes valeurs, des
règles globales (toutes zones) sont créées au lieu d'une copie par zone.

Les alertes de seuil encore actives (anciens codes) sont clôturées avec la
résolution « migrated » : le nouveau moteur prendra le relais à la prochaine
mesure.
"""

from django.db import migrations
from django.utils import timezone


LEGACY_CODES = [
    "TEMPERATURE_OUT_OF_RANGE",
    "HUMIDITY_OUT_OF_RANGE",
    "HIGH_SOUND_LEVEL",
    "SOUND_WARNING",
]


def rules_for_profile(profile):
    rules = []
    if profile.temperature_min < profile.temperature_max:
        rules.append(
            dict(
                name="Température hors plage",
                metric="temperature",
                operator="outside_range",
                threshold=profile.temperature_min,
                threshold_high=profile.temperature_max,
                severity="warning",
            )
        )
    if profile.humidity_min < profile.humidity_max:
        rules.append(
            dict(
                name="Humidité hors plage",
                metric="humidity",
                operator="outside_range",
                threshold=profile.humidity_min,
                threshold_high=profile.humidity_max,
                severity="warning",
            )
        )
    rules.append(
        dict(
            name="Niveau sonore élevé",
            metric="sound_level",
            operator="gte",
            threshold=profile.sound_warning,
            threshold_high=None,
            severity="warning",
        )
    )
    rules.append(
        dict(
            name="Niveau sonore critique",
            metric="sound_level",
            operator="gt",
            threshold=profile.sound_critical,
            threshold_high=None,
            severity="critical",
        )
    )
    return rules


def profile_signature(profile):
    return (
        profile.enabled,
        profile.temperature_min,
        profile.temperature_max,
        profile.humidity_min,
        profile.humidity_max,
        profile.sound_warning,
        profile.sound_critical,
    )


def convert(apps, schema_editor):
    ThresholdProfile = apps.get_model("core", "ThresholdProfile")
    AlarmRule = apps.get_model("core", "AlarmRule")
    Alert = apps.get_model("core", "Alert")

    description = "Règle créée automatiquement à partir de l'ancien profil de seuils."
    profiles = list(ThresholdProfile.objects.select_related("zone"))
    if profiles and not AlarmRule.objects.exists():
        if len({profile_signature(profile) for profile in profiles}) == 1:
            reference = profiles[0]
            for rule in rules_for_profile(reference):
                AlarmRule.objects.create(
                    zone=None,
                    enabled=reference.enabled,
                    description=description,
                    **rule,
                )
        else:
            for profile in profiles:
                for rule in rules_for_profile(profile):
                    AlarmRule.objects.create(
                        zone=profile.zone,
                        enabled=profile.enabled,
                        description=description,
                        **rule,
                    )

    Alert.objects.filter(code__in=LEGACY_CODES, active=True).update(
        active=False,
        resolved_at=timezone.now(),
        resolution="migrated",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_alarm_rules"),
    ]

    operations = [
        migrations.RunPython(convert, reverse_code=migrations.RunPython.noop),
    ]
