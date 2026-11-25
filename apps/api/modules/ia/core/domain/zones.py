"""Correspondance confirmée entre numéros de modèle et codes de zone GRIDD."""

from types import MappingProxyType

ZONE_MODEL_MAPPING = MappingProxyType(
    {
        1: "open-workspace",
        2: "server-equipment-room",
        3: "professors-office",
        4: "individual-work-cubicle-01",
        5: "meeting-room",
        6: "individual-work-cubicle-02",
    }
)
