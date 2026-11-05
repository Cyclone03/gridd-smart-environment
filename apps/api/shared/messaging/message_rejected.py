class MessageRejected(Exception):
    """Message définitivement invalide (format, contenu, incohérence).

    Le consommateur le journalise puis valide son offset : rejouer un message
    invalide ne le rendrait pas valide et bloquerait la partition.
    """
