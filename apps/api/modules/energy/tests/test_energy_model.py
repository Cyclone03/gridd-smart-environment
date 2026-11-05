from django.test import SimpleTestCase

from modules.energy.domain.energy_aggregator import EnergyAggregator
from modules.energy.domain.energy_defaults import EnergyDefaults
from modules.energy.domain.energy_model import EnergyModel


class EnergyModelTests(SimpleTestCase):
    def setUp(self):
        self.model = EnergyModel()

    def test_office_needs_heating_in_winter(self):
        profile = EnergyDefaults.for_zone_type("office")  # 20 m², 8 W/m², 150 W + 120 W/pers., UA 20 W/K
        power = self.model.power(profile, indoor_temperature=22, occupancy=1)
        self.assertEqual((power.lighting_w, power.equipment_w), (160, 270))
        # Pertes (20 + 1,2 × 10 × 1) × 17 = 544 W ; apports 75 + 160 + 270 = 505 W ; besoin 39 W ÷ COP 2,5.
        self.assertAlmostEqual(power.heating_w, 15.6)
        self.assertEqual(power.cooling_w, 0)
        self.assertTrue(power.hvac_estimated)

    def test_server_room_needs_cooling(self):
        profile = EnergyDefaults.for_zone_type("server_room")
        power = self.model.power(profile, indoor_temperature=22, occupancy=0)
        self.assertEqual(power.heating_w, 0)
        self.assertGreater(power.cooling_w, 1000)
        self.assertAlmostEqual(power.lighting_w, 25 * 5 * 0.1)  # éclairage de veille sans occupant

    def test_unknown_indoor_temperature_skips_hvac(self):
        power = self.model.power(EnergyDefaults.for_zone_type("office"), indoor_temperature=None, occupancy=2)
        self.assertFalse(power.hvac_estimated)
        self.assertEqual(power.heating_w + power.cooling_w, 0)

    def test_energy_over_an_interval(self):
        power = self.model.power(EnergyDefaults.for_zone_type("office"), indoor_temperature=None, occupancy=1)
        energy = power.energy_wh(1800)
        self.assertEqual(energy["lighting_wh"], 80)
        self.assertEqual(energy["total_wh"], 215)


class EnergyAggregatorTests(SimpleTestCase):
    def test_totals(self):
        rows = [
            {"zone__code": "a", "duration_seconds": 1800, "lighting_wh": 50, "equipment_wh": 100, "heating_wh": 0,
             "cooling_wh": 50, "total_wh": 200},
            {"zone__code": "a", "duration_seconds": 1800, "lighting_wh": 50, "equipment_wh": 100, "heating_wh": 0,
             "cooling_wh": 50, "total_wh": 200},
        ]
        totals = EnergyAggregator().totals(rows)
        self.assertEqual((totals["total_kwh"], totals["covered_hours"], totals["average_power_w"]), (0.4, 1.0, 400.0))
        self.assertIsNone(EnergyAggregator().totals([])["average_power_w"])
