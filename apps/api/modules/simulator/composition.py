"""Racine de composition du module Simulator."""

from django.utils import timezone

from modules.simulator.adapters.messaging.sensor_topic_publisher import SensorTopicPublisher
from modules.simulator.adapters.persistence.simulated_sensor_repository import SimulatedSensorRepository
from modules.simulator.core.services.simulator_service import SimulatorService
from shared.messaging import Messaging


def simulator_service() -> SimulatorService:
    return SimulatorService(
        sensors=SimulatedSensorRepository(),
        publisher=SensorTopicPublisher(Messaging.current().publisher("sensors")),
        clock=timezone.now,
    )
