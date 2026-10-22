from django.shortcuts import get_object_or_404, render

from .models import Alert, Observation, Zone


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
