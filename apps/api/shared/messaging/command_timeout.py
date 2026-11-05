from .messaging_unavailable import MessagingUnavailable


class CommandTimeout(MessagingUnavailable):
    """Aucune réponse à une commande dans le délai imparti."""
