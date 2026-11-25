class AlertSeverity:
    """Sévérité d'une alerte."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

    CHOICES = ((INFO, "Info"), (WARNING, "Attention"), (CRITICAL, "Critique"))
