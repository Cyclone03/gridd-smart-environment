from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from modules.ingestion.domain.past_reading import PastReading
from modules.ingestion.domain.quality_assessor import QualityAssessor
from modules.ingestion.domain.quality_profile import QualityProfile


class QualityAssessorTests(SimpleTestCase):
    """Logique pure du contrôle de qualité, sans base de données."""

    def setUp(self):
        self.assessor = QualityAssessor()
        self.now = timezone.now()
        self.profile = QualityProfile(enabled=True, stuck_after_minutes=5, rate_limits={"temperature": 1})

    def assess(self, value, history, profile=None, observed_at=None):
        return self.assessor.assess(
            metric="temperature",
            value=value,
            observed_at=observed_at or self.now,
            now=self.now,
            history=history,
            profile=profile,
        )

    def past(self, minutes_ago, value):
        moment = self.now - timedelta(minutes=minutes_ago)
        return PastReading(value=value, observed_at=moment, received_at=moment)

    def test_first_reading_is_normal(self):
        self.assertEqual(self.assess(22, []).status, "normal")

    def test_physical_limits(self):
        result = self.assess(-40, [])
        self.assertEqual(result.status, "invalid")
        self.assertIn("-20", result.reason)

    def test_rate_limit_only_when_profile_enabled(self):
        history = [self.past(1, 20)]
        self.assertEqual(self.assess(25, history, self.profile).status, "suspicious")
        disabled = QualityProfile(enabled=False, stuck_after_minutes=5, rate_limits={"temperature": 1})
        self.assertEqual(self.assess(25, history, disabled).status, "normal")

    def test_stuck_sensor_uses_profile_or_default_delay(self):
        history = [self.past(4, 22), self.past(8, 22), self.past(9, 21)]
        self.assertEqual(self.assess(22, history, self.profile).status, "suspicious")
        self.assertEqual(self.assess(22, history, None).status, "normal")  # défaut : 15 min

    def test_previous_reading_is_the_latest_before_the_observation(self):
        # Message en retard : la variation est comparée à la mesure qui le précède.
        history = [self.past(0, 30), self.past(10, 21)]
        late = self.assess(21.5, history, self.profile, observed_at=self.now - timedelta(minutes=5))
        self.assertEqual(late.status, "normal")
