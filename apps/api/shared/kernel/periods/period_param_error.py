class PeriodParamError(ValueError):
    """Paramètre de période ou de requête invalide (réponse 400 avec erreur par champ)."""

    def __init__(self, message, field=None, field_message=None):
        super().__init__(message)
        self.message = message
        self.field = field
        self.field_message = field_message or message
