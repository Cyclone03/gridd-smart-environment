from shared.kernel.vocabulary import ZoneType

from .zone_descriptor import ZoneDescriptor


class ZoneResolver:
    """Détermine la zone d'une mesure à partir des métadonnées du capteur."""

    TYPES_BY_CODE = {
        "server-equipment-room": ZoneType.SERVER_ROOM,
        "professors-office": ZoneType.OFFICE,
        "meeting-room": ZoneType.MEETING_ROOM,
        "open-workspace": ZoneType.OPEN_WORKSPACE,
    }
    TYPES_BY_PREFIX = (("individual-work-cubicle", ZoneType.CUBICLE),)

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
