"""Administration Django des données GRIDD (back-office du module Database).

Chaque classe d'administration est dans son propre fichier ; leur import
suffit à les enregistrer.
"""

from .alarm_rule_admin import AlarmRuleAdmin
from .alarm_rule_state_admin import AlarmRuleStateAdmin
from .alert_admin import AlertAdmin
from .observation_admin import ObservationAdmin
from .sensor_admin import SensorAdmin
from .threshold_profile_admin import ThresholdProfileAdmin
from .zone_admin import ZoneAdmin

__all__ = [
    "AlarmRuleAdmin",
    "AlarmRuleStateAdmin",
    "AlertAdmin",
    "ObservationAdmin",
    "SensorAdmin",
    "ThresholdProfileAdmin",
    "ZoneAdmin",
]
