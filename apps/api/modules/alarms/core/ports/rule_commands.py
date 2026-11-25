from typing import Protocol


class RuleCommands(Protocol):
    """Écriture des règles par le propriétaire des données (commande avec
    réponse). Lève une erreur si la commande échoue."""

    def create(self, fields: dict) -> dict:
        """Retourne au moins ``{"rule_id": ...}``."""

    def update(self, rule_id, fields: dict) -> dict: ...

    def remove(self, rule_id) -> dict: ...
