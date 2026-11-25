import random


class ValueGenerator:
    """Marche aléatoire bornée, propre à chaque type de mesure."""

    DEFAULTS = {
        "temperature": 22.0,
        "humidity": 42.0,
        "co2": 600.0,
        "sound_level": 42.0,
        "occupancy": 4.0,
    }
    # (pas maximal, minimum, maximum, décimales)
    STEPS = {
        "temperature": (0.12, 18.0, 28.0, 1),
        "humidity": (0.4, 25.0, 70.0, 1),
        "co2": (8.0, 400.0, 1600.0, 0),
        "sound_level": (0.8, 30.0, 85.0, 1),
        "occupancy": (1.0, 0.0, 35.0, 0),
    }

    def __init__(self, rng=None):
        self._rng = rng or random.Random()

    def initial(self, metric, last_value=None) -> float:
        return last_value if last_value is not None else self.DEFAULTS[metric]

    def next(self, metric, current) -> float:
        step, minimum, maximum, digits = self.STEPS[metric]
        if metric == "occupancy":
            value = current + self._rng.choice([-1, 0, 0, 0, 1])
        else:
            value = current + self._rng.uniform(-step, step)
        return round(min(max(value, minimum), maximum), digits)
