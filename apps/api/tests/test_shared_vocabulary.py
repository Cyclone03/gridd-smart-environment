from django.test import SimpleTestCase

from modules.alarms.core.domain.alarm_status import AlarmStatus
from modules.database.models import AlarmRuleState, Alert, ClimatePrediction, Observation, Zone
from shared.kernel.vocabulary import AlertResolution, AlertSeverity, PredictionMode, QualityStatus, ZoneType


def constants(cls):
    return {value for name, value in vars(cls).items() if name.isupper() and isinstance(value, str)}


class SharedVocabularyTests(SimpleTestCase):
    """Les valeurs du noyau pur (utilisées par les cœurs des modules) sont
    exactement celles stockées en base."""

    def test_kernel_values_match_model_choices(self):
        self.assertEqual(constants(QualityStatus), set(Observation.QualityStatus.values))
        self.assertEqual(QualityStatus.LABELS, dict(Observation.QualityStatus.choices))
        self.assertEqual(constants(AlertSeverity), set(Alert.Severity.values))
        self.assertEqual(AlertSeverity.CHOICES, tuple(Alert.Severity.choices))
        self.assertEqual(constants(AlertResolution), set(Alert.Resolution.values))
        self.assertEqual(constants(ZoneType), set(Zone.ZoneType.values))
        self.assertEqual(PredictionMode.VALUES, set(ClimatePrediction.PredictionMode.values))
        self.assertEqual(constants(AlarmStatus), set(AlarmRuleState.Status.values))
