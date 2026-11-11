"""Schéma de la base GRIDD.

Interface publique du module Database pour les autres modules : ils peuvent
**lire** ces modèles (via leurs propres repositories), jamais les écrire.
Les anciens modèles confort/énergie restent enregistrés pour préserver leur
schéma et leurs données, mais ne sont plus alimentés par un traitement actif.
"""

from .alarm_rule import AlarmRule
from .alarm_rule_state import AlarmRuleState
from .alert import Alert
from .comfort_assessment import ComfortAssessment
from .comfort_profile import ComfortProfile
from .energy_estimate import EnergyEstimate
from .energy_profile import EnergyProfile
from .observation import Observation
from .sensor import Sensor
from .threshold_profile import ThresholdProfile
from .zone import Zone

__all__ = [
    "AlarmRule",
    "AlarmRuleState",
    "Alert",
    "ComfortAssessment",
    "ComfortProfile",
    "EnergyEstimate",
    "EnergyProfile",
    "Observation",
    "Sensor",
    "ThresholdProfile",
    "Zone",
]
