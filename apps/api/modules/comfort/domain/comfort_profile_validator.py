class ComfortProfileValidator:
    """Cohérence d'une plage de confort (les bornes de chaque champ sont
    vérifiées par le serializer)."""

    def errors(self, values) -> dict:
        errors = {}
        if values["temperature_min"] >= values["temperature_max"]:
            errors["temperature_max"] = "La température maximale doit être supérieure à la minimale."
        if values["humidity_min"] >= values["humidity_max"]:
            errors["humidity_max"] = "L'humidité maximale doit être supérieure à la minimale."
        return errors
