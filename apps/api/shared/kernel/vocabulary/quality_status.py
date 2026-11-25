class QualityStatus:
    """Qualité d'une mesure, attribuée par l'ingestion."""

    NORMAL = "normal"
    SUSPICIOUS = "suspicious"
    INVALID = "invalid"

    LABELS = {NORMAL: "Normal", SUSPICIOUS: "Suspecte", INVALID: "Invalide"}

    @classmethod
    def label(cls, value) -> str:
        return cls.LABELS.get(value, str(value))
