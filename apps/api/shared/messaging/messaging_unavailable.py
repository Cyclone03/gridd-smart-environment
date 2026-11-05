class MessagingUnavailable(Exception):
    """Kafka (ou le module destinataire d'une commande) est injoignable.

    Erreur transitoire : un consommateur réessaie le message, l'API répond 503.
    """
