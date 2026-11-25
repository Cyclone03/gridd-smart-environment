"""Identité d'un capteur : un capteur par espace et par type de mesure.

Les nœuds physiques GRIDD (``environmental-node03``…) peuvent être déplacés ou
réétiquetés : ce qui compte pour GRIDD est la mesure d'un espace. Le
``node_id`` reçu est conservé comme information de provenance
(métadonnée ``source_node_id`` du capteur).
"""


def sensor_key(zone_code: str, metric: str) -> str:
    """Identifiant stable du capteur d'une zone pour un type de mesure
    (ex. ``individual-work-cubicle-01-temperature``)."""
    return f"{zone_code}-{metric}"
