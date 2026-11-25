from typing import Protocol


class AlarmRuleStore(Protocol):
    """Règles d'alarme (objets exposant ``pk``). Lève ``CommandFailed`` pour
    une commande invalide."""

    def create(self, fields): ...

    def update(self, rule_id, fields) -> tuple[object, list[str]]: ...

    def delete(self, rule_id): ...
