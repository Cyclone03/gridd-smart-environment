from shared.kernel.vocabulary import ZoneType

from .zone_descriptor import ZoneDescriptor


class ZoneResolver:
    """Détermine la zone d'une mesure.

    Dans l'ordre :

    1. métadonnées du message : ``zone`` objet (``id``/``code``, ``label``/``name``)
       ou chaîne, ou ``zone_id`` / ``zoneId`` / ``zone_code`` / ``zoneCode`` ;
    2. correspondance configurée nœud → zone (``GRIDD_NODE_ZONES``), pour les
       nœuds qui n'annoncent pas leur zone.

    Retourne ``None`` si aucune zone n'est connue : la mesure est alors
    rejetée. Le ``node_id`` n'est **jamais** utilisé comme code de zone (il
    créait un « espace » par nœud : node01, node02…).
    """

    TYPES_BY_CODE = {
        "server-equipment-room": ZoneType.SERVER_ROOM,
        "professors-office": ZoneType.OFFICE,
        "meeting-room": ZoneType.MEETING_ROOM,
        "open-workspace": ZoneType.OPEN_WORKSPACE,
    }
    TYPES_BY_PREFIX = (("individual-work-cubicle", ZoneType.CUBICLE),)
    CODE_KEYS = ("zone_id", "zoneId", "zone_code", "zoneCode")

    def __init__(self, node_zones=None):
        self._node_zones = dict(node_zones or {})

    def resolve(self, metadata, node_id) -> ZoneDescriptor | None:
        code, name = self._from_metadata(metadata)
        if not code:
            code = self._node_zones.get(node_id)
        if not code:
            return None
        return ZoneDescriptor(code=code, name=name, zone_type=self.infer_type(code))

    def _from_metadata(self, metadata):
        zone = metadata.get("zone")
        if isinstance(zone, dict):
            code = self._text(zone.get("id")) or self._text(zone.get("code"))
            return code, self._text(zone.get("label")) or self._text(zone.get("name"))
        if self._text(zone):
            return self._text(zone), None
        for key in self.CODE_KEYS:
            if self._text(metadata.get(key)):
                return self._text(metadata.get(key)), None
        return None, None

    @staticmethod
    def _text(value):
        return value.strip() if isinstance(value, str) and value.strip() else None

    def infer_type(self, code) -> str | None:
        if code in self.TYPES_BY_CODE:
            return self.TYPES_BY_CODE[code]
        for prefix, zone_type in self.TYPES_BY_PREFIX:
            if code.startswith(prefix):
                return zone_type
        return None
