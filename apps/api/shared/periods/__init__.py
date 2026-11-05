"""Périodes d'analyse partagées par les modules de consultation (historique,
confort, énergie) : mêmes paramètres ``start``/``end``/``bucket_minutes``,
même validation, mêmes créneaux."""

from .period import Period
from .period_param_error import PeriodParamError
from .period_parser import PeriodParser
from .time_bucket import TimeBucket

__all__ = ["Period", "PeriodParamError", "PeriodParser", "TimeBucket"]
