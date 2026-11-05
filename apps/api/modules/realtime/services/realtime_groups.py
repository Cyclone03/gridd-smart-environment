class RealtimeGroups:
    """Groupes Channels : tableau de bord global et une zone précise."""

    DASHBOARD = "dashboard"

    @staticmethod
    def zone(zone_code) -> str:
        return f"zone_{zone_code}"
