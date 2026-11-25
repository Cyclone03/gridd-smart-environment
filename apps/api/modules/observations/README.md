# Module Observations

Consultation des zones, capteurs, mesures, dernières prédictions climatiques et
dernier instantané météo (lecture seule).

## Contrat

| | |
|---|---|
| HTTP | `/api/zones/`, `/api/zones/<id>/`, `/api/zones/<code>/latest/`, `/api/sensors/`, `/api/observations/` (`?zone=&type=`), `/api/observations/latest/`, `/api/climate-predictions/latest/`, `/api/weather/latest/` |
| Kafka | aucun |
| Données lues | `Zone`, `Sensor`, `ThresholdProfile`, `Observation`, `ClimatePrediction`, `WeatherSnapshot` |

## Structure

```text
core/
  ports/      ObservationReader, ZoneReader, SensorReader,
              ClimatePredictionReader, WeatherSnapshotReader
  services/   ObservationService, ZoneService, SensorService, WeatherSnapshotService
adapters/
  persistence/   un repository ORM par port
  http/          contrôleurs DRF, serializers, urls.py
composition.py   observation_service(), zone_service(), sensor_service(), weather_snapshot_service()
```

Les services ne connaissent pas la forme des objets lus : les repositories et
les serializers HTTP forment une paire cohérente (ici, des instances de modèles
Django). Un autre projet peut fournir des repositories renvoyant d'autres
objets, avec ses propres serializers.

## Réutiliser le module

Ajouter `modules.observations.apps.ObservationsConfig` à `INSTALLED_APPS` et
inclure `modules.observations.adapters.http.urls`.
