class ComfortStatus:
    """États possibles d'un facteur de confort (température ou humidité)."""

    OK = "ok"
    UNKNOWN = "unknown"

    # (très en dessous, légèrement en dessous, légèrement au-dessus, très au-dessus)
    TEMPERATURE = ("too_cold", "cool", "warm", "too_hot")
    HUMIDITY = ("too_dry", "dry", "humid", "too_humid")

    @classmethod
    def is_severe(cls, status) -> bool:
        return status.startswith("too_")
