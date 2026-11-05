from dataclasses import dataclass


@dataclass(frozen=True)
class ZoneDescriptor:
    """Zone désignée par un message capteur.

    ``zone_type`` vaut ``None`` lorsqu'il ne peut pas être déduit : le type
    déjà enregistré n'est alors pas modifié.
    """

    code: str
    name: str | None
    zone_type: str | None
