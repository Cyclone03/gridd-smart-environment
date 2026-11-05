class Operator:
    """Opérateurs de comparaison disponibles pour les règles d'alarme."""

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    OUTSIDE_RANGE = "outside_range"
    INSIDE_RANGE = "inside_range"

    ALL = (GT, GTE, LT, LTE, OUTSIDE_RANGE, INSIDE_RANGE)

    RANGE = frozenset({OUTSIDE_RANGE, INSIDE_RANGE})

    LABELS = {
        GT: "Supérieur à",
        GTE: "Supérieur ou égal à",
        LT: "Inférieur à",
        LTE: "Inférieur ou égal à",
        OUTSIDE_RANGE: "En dehors de l'intervalle",
        INSIDE_RANGE: "À l'intérieur de l'intervalle",
    }

    SYMBOLS = {
        GT: ">",
        GTE: "≥",
        LT: "<",
        LTE: "≤",
    }

    @classmethod
    def is_range(cls, operator):
        return operator in cls.RANGE
