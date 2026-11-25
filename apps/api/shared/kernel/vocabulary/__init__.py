"""Valeurs partagées par plusieurs modules (statuts, sévérités, types de zone).

Ce sont les valeurs stockées en base : les ``TextChoices`` des modèles du
module Database reprennent exactement ces valeurs (vérifié par les tests).
"""

from .alert_resolution import AlertResolution
from .alert_severity import AlertSeverity
from .prediction_mode import PredictionMode
from .quality_status import QualityStatus
from .zone_type import ZoneType

__all__ = ["AlertResolution", "AlertSeverity", "PredictionMode", "QualityStatus", "ZoneType"]
