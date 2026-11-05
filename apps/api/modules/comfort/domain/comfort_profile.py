from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ComfortProfile:
    """Plages de confort d'un espace.

    - dans ``[min ; max]`` : confortable ;
    - au plus ``tolerance`` en dehors : acceptable ;
    - au-delà : inconfortable.
    """

    temperature_min: float
    temperature_max: float
    temperature_tolerance: float
    humidity_min: float
    humidity_max: float
    humidity_tolerance: float

    FIELDS = (
        "temperature_min",
        "temperature_max",
        "temperature_tolerance",
        "humidity_min",
        "humidity_max",
        "humidity_tolerance",
    )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_values(cls, values) -> "ComfortProfile":
        return cls(**{field: float(values[field]) for field in cls.FIELDS})
