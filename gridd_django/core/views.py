from django.shortcuts import get_object_or_404, render

from .models import Alert, Observation, Zone, ThresholdProfile

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .serializers import ThresholdProfileSerializer


METRIC_DEFINITIONS = {
    "temperature": {
        "label": "Température",
        "unit": "°C",
    },
    "humidity": {
        "label": "Humidité",
        "unit": "%",
    },
    "co2": {
        "label": "CO₂",
        "unit": "ppm",
    },
    "sound_level": {
        "label": "Niveau sonore",
        "unit": "dBA",
    },
    "occupancy": {
        "label": "Occupation",
        "unit": "personnes",
    },
}


def dashboard(request):
    return render(
        request,
        "core/react_dashboard.html",
    )


def legacy_dashboard(request):
    zones = (
        Zone.objects
        .filter(active=True)
        .order_by("name")
    )

    cards = []

    for zone in zones:
        metrics = []

        for metric_type, definition in METRIC_DEFINITIONS.items():
            observation = (
                Observation.objects
                .filter(
                    zone=zone,
                    type=metric_type,
                )
                .order_by(
                    "-observed_at",
                    "-received_at",
                )
                .first()
            )

            metrics.append(
                {
                    "type": metric_type,
                    "label": definition["label"],
                    "unit": definition["unit"],
                    "value": (
                        observation.value
                        if observation
                        else None
                    ),
                    "available": (
                        observation is not None
                    ),
                    "quality_status": (
                        observation.quality_status
                        if observation
                        else None
                    ),
                }
            )

        cards.append(
            {
                "zone": zone,
                "metrics": metrics,
                "active_alerts": (
                    Alert.objects.filter(
                        zone=zone,
                        active=True,
                    ).count()
                ),
            }
        )

    return render(
        request,
        "core/dashboard.html",
        {
            "cards": cards,
        },
    )


def zone_dashboard(request, code):
    zone = get_object_or_404(
        Zone,
        code=code,
        active=True,
    )

    observations = (
        Observation.objects
        .filter(zone=zone)
        .select_related("sensor")
        .order_by(
            "-observed_at",
            "-received_at",
        )[:200]
    )

    alerts = (
        Alert.objects
        .filter(zone=zone)
        .order_by("-created_at")[:50]
    )

    latest = {}
    metrics = []

    for metric_type in METRIC_DEFINITIONS:
        observation = (
            Observation.objects
            .filter(
                zone=zone,
                type=metric_type,
            )
            .order_by(
                "-observed_at",
                "-received_at",
            )
            .first()
        )

        if observation:
            latest[metric_type] = observation

        metrics.append(
            {
                "type": metric_type,
                "label": METRIC_DEFINITIONS[metric_type]["label"],
                "unit": METRIC_DEFINITIONS[metric_type]["unit"],
                "observation": observation,
            }
        )

    return render(
        request,
        "core/zone_dashboard.html",
        {
            "zone": zone,
            "latest": latest,
            "metrics": metrics,
            "observations": observations,
            "alerts": alerts,
        },
    )


@api_view(["PATCH"])
def update_temperature_min(request, zone_code):
    try:
        profile = ThresholdProfile.objects.select_related("zone").get(
            zone__code=zone_code
        )
    except ThresholdProfile.DoesNotExist:
        return Response(
            {"error": "Profil de seuil introuvable."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Champs autorisés et valeurs actuelles par défaut
    fields = {
        "temperature_min": profile.temperature_min,
        "temperature_max": profile.temperature_max,
        "humidity_min": profile.humidity_min,
        "humidity_max": profile.humidity_max,
        "sound_warning": profile.sound_warning,
        "sound_critical": profile.sound_critical,
        "max_temperature_delta_per_minute":
            profile.max_temperature_delta_per_minute,
        "max_humidity_delta_per_minute":
            profile.max_humidity_delta_per_minute,
    }

    # Convertir et valider les valeurs fournies
    updated_values = {}

    for field, current_value in fields.items():
        if field not in request.data:
            updated_values[field] = current_value
            continue

        value = request.data[field]

        if value is None or isinstance(value, bool):
            return Response(
                {"error": f"Le champ {field} doit être un nombre."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            value = float(value)
        except (ValueError, TypeError):
            return Response(
                {"error": f"Le champ {field} doit être un nombre."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        import math
        if not math.isfinite(value):
            return Response(
                {"error": f"Le champ {field} doit être un nombre fini."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_values[field] = value

    # Vérifier les limites physiques
    if not (
        -50 <= updated_values["temperature_min"] <= 100
        and -50 <= updated_values["temperature_max"] <= 100
    ):
        return Response(
            {
                "error": (
                    "Les températures doivent être comprises "
                    "entre -50 et 100 °C."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        updated_values["temperature_min"]
        >= updated_values["temperature_max"]
    ):
        return Response(
            {
                "error": (
                    "La température minimale doit être "
                    "inférieure à la température maximale."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not (
        0 <= updated_values["humidity_min"] <= 100
        and 0 <= updated_values["humidity_max"] <= 100
    ):
        return Response(
            {
                "error": (
                    "L'humidité doit être comprise entre 0 et 100 %."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if updated_values["humidity_min"] >= updated_values["humidity_max"]:
        return Response(
            {
                "error": (
                    "L'humidité minimale doit être "
                    "inférieure à l'humidité maximale."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        updated_values["sound_warning"] < 0
        or updated_values["sound_critical"] < 0
    ):
        return Response(
            {
                "error": "Les seuils sonores ne peuvent pas être négatifs."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        updated_values["sound_warning"]
        >= updated_values["sound_critical"]
    ):
        return Response(
            {
                "error": (
                    "Le seuil sonore d'avertissement doit être "
                    "inférieur au seuil critique."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        updated_values["max_temperature_delta_per_minute"] < 0
        or updated_values["max_humidity_delta_per_minute"] < 0
    ):
        return Response(
            {
                "error": "Les variations maximales ne peuvent pas être négatives."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Enregistrer uniquement les champs effectivement envoyés
    changed_fields = []

    for field in fields:
        if field in request.data:
            setattr(profile, field, updated_values[field])
            changed_fields.append(field)

    if changed_fields:
        profile.save(update_fields=changed_fields)

    return Response(
        ThresholdProfileSerializer(profile).data,
        status=status.HTTP_200_OK,
    )
