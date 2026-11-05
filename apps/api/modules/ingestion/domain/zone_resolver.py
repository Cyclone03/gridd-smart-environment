from modules.database.models import Zone

from .zone_descriptor import ZoneDescriptor


class ZoneResolver:
    """Détermine la zone d'une mesure à partir des métadonnées du capteur."""

    TYPES_BY_CODE = {
        "server-equipment-room": Zone.ZoneType.SERVER_ROOM,
        "professors-office": Zone.ZoneType.OFFICE,
        "meeting-room": Zone.ZoneType.MEETING_ROOM,
        "open-workspace": Zone.ZoneType.OPEN_WORKSPACE,
    }
    TYPES_BY_PREFIX = (("individual-work-cubicle", Zone.ZoneType.CUBICLE),)

    def resolve(self, metadata, node_id) -> ZoneDescriptor:
        zone_metadata = metadata.get("zone") if isinstance(metadata.get("zone"), dict) else {}
        code = zone_metadata.get("id") or node_id
        return ZoneDescriptor(code=code, name=zone_metadata.get("label") or None, zone_type=self.infer_type(code))

    def infer_type(self, code) -> str | None:
        if code in self.TYPES_BY_CODE:
            return self.TYPES_BY_CODE[code]
        for prefix, zone_type in self.TYPES_BY_PREFIX:
            if code.startswith(prefix):
                return zone_type
        return None
