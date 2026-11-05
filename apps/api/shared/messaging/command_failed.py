class CommandFailed(Exception):
    """Refus explicite d'une commande par le module qui la traite.

    Transporté dans la réponse ``command.failed`` puis relevé chez l'émetteur ;
    l'API le traduit en réponse HTTP (404, 400 ou 500 selon ``code``).
    """

    NOT_FOUND = "not_found"
    INVALID = "invalid"
    ERROR = "error"

    def __init__(self, code, message, errors=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or {}

    def to_payload(self):
        return {"code": self.code, "message": self.message, "errors": self.errors}

    @classmethod
    def from_payload(cls, payload):
        error = payload.get("error") or {}
        return cls(
            error.get("code", cls.ERROR),
            error.get("message", "La commande a échoué."),
            error.get("errors") or {},
        )
